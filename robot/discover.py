"""Discovery: for every company, find its careers site and work out which
hiring system it uses. Run by hand (or monthly); the regular check then
only reads the sites found here.

Order of preference for each company:
  1. data/overrides.json  - settings a person has fixed by hand (always win)
  2. data/seeds.json      - a known careers page link; the page is opened and
                            its hiring system detected
  3. guessing             - try the company's name on hiring systems that
                            have public feeds (Greenhouse, Lever, Ashby,
                            SmartRecruiters, Workable)
Companies still unmatched are listed in data/discovery_report.md.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from .detect import detect
from .http import Blocked, Http

DATA = Path(__file__).resolve().parent.parent / "data"


def load_companies() -> list[dict]:
    """Companies in scope: investment banking (IB) and private equity (PE)."""
    with open(DATA / "companies.csv", newline="", encoding="utf-8") as f:
        return [c for c in csv.DictReader(f) if c.get("segment")]


def load_json(name: str, default):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _norm(s: str) -> set[str]:
    stop = {"the", "and", "co", "group", "plc", "ltd", "llp", "inc", "partners", "capital", "management", "&"}
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in stop}


def _same_company(a: str, b: str) -> bool:
    x, y = _norm(a), _norm(b)
    return bool(x and y) and len(x & y) / max(1, min(len(x), len(y))) >= 0.6


def slugs(name: str) -> list[str]:
    base = re.sub(r"\(.*?\)", "", name).replace("&", "and")
    words = re.findall(r"[A-Za-z0-9]+", base)
    joined = "".join(words).lower()
    dashed = "-".join(words).lower()
    return list(dict.fromkeys([joined, dashed]))


def guess(company: dict, http: Http) -> tuple[str, dict] | None:
    name = company["name"]
    for slug in slugs(name):
        if len(slug) < 4:
            continue
        try:  # Greenhouse tells us the board's company name, so we can verify it
            info = http.get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}")
            if _same_company(info.get("name", ""), name):
                return "greenhouse", {"board": slug}
        except (httpx.HTTPError, Blocked, ValueError):
            pass
        try:
            info = http.get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
            # Workable answers for almost any name, so also require live jobs
            if _same_company(info.get("name", ""), name) and info.get("jobs"):
                return "workable", {"account": slug}
        except (httpx.HTTPError, Blocked, ValueError):
            pass
        # The next systems don't return a company name: accept only the full-name slug
        # with at least one live job, and mark the match for a person to confirm.
        try:
            jobs = http.get_json(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json", "limit": 1})
            if isinstance(jobs, list) and jobs:
                return "lever", {"site": slug, "unconfirmed": True}
        except (httpx.HTTPError, Blocked, ValueError):
            pass
        try:
            data = http.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
            if data.get("jobs"):
                return "ashby", {"board": slug, "unconfirmed": True}
        except (httpx.HTTPError, Blocked, ValueError):
            pass
        try:
            data = http.get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"limit": 1})
            if data.get("totalFound", 0) > 0:
                return "smartrecruiters", {"company": slug, "unconfirmed": True}
        except (httpx.HTTPError, Blocked, ValueError):
            pass
    return None


def rendered_html(url: str) -> tuple[str, str]:
    """Open a page in a real (screenless) browser for sites built with JavaScript."""
    from .readers.browser import _browser, _lock
    from .http import USER_AGENT

    with _lock:
        page = _browser().new_page(user_agent=USER_AGENT)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            return page.url, page.content()
        finally:
            page.close()


def from_seed(url: str, http: Http, allow_browser: bool = True) -> tuple[str, dict, str]:
    try:
        final, html = http.final_url_and_text(url)
    except Blocked:
        return "", {}, "robots.txt asks tools not to read this page"
    except httpx.HTTPError as e:
        final, html = url, ""
        note = f"plain download failed ({e.__class__.__name__}); tried the browser"
    else:
        note = ""
    found = detect(final, html)
    if not found and not allow_browser:
        return "needs-browser", {}, note
    if not found:
        try:
            final, html = rendered_html(url)
            found = detect(final, html)
        except Exception as e:  # noqa: BLE001 - report and fall back
            note = f"browser failed: {e.__class__.__name__}"
    if found:
        return found[0], found[1], note
    return "browser", {"url": final}, (note or "no known hiring system found; reading the page in the browser")


def discover_one(company: dict, seeds: dict, overrides: dict, http: Http) -> dict:
    cid = company["id"]
    entry = {"id": cid, "name": company["name"], "sector": company["sector"], "segment": company["segment"],
             "checked": dt.date.today().isoformat()}
    if cid in overrides:
        return {**entry, **overrides[cid], "how": "set by hand"}
    seed = seeds.get(cid)
    if seed:
        system, params, note = from_seed(seed, http, allow_browser=False)
        if system == "needs-browser":
            return {**entry, "system": None, "careers_url": seed, "how": "careers page", "needs_browser": True}
        if system:
            return {**entry, "system": system, "params": params, "careers_url": seed, "how": "careers page", "note": note}
        return {**entry, "system": None, "careers_url": seed, "how": "careers page", "note": note}
    g = guess(company, http)
    if g:
        return {**entry, "system": g[0], "params": g[1], "how": "name guess"}
    return {**entry, "system": None, "how": "not found", "note": "needs a careers page link in data/seeds.json"}


def write_report(sources: dict) -> None:
    by_system: dict[str, int] = {}
    missing, unconfirmed, fallback = [], [], []
    for s in sources.values():
        sys_ = s.get("system") or "none"
        by_system[sys_] = by_system.get(sys_, 0) + 1
        if not s.get("system"):
            missing.append(s)
        elif (s.get("params") or {}).get("unconfirmed"):
            unconfirmed.append(s)
        elif s["system"] == "browser":
            fallback.append(s)
    lines = [f"# Discovery report ({dt.date.today().isoformat()})", "",
             f"{len(sources)} companies. {len(sources) - len(missing)} have a source; {len(missing)} still need a careers link.", "",
             "| Hiring system | Companies |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_system.items(), key=lambda kv: -kv[1])]
    lines += ["", "## Needs a careers page link", ""]
    lines += [f"- {s['name']} ({s['sector']})" for s in sorted(missing, key=lambda s: (s['segment'], s['name']))]
    lines += ["", "## Matched by name guess: please confirm", ""]
    lines += [f"- {s['name']}: {s['system']} `{s['params']}`" for s in unconfirmed]
    lines += ["", "## Read with the browser fallback", ""]
    lines += [f"- {s['name']}: {(s.get('params') or {}).get('url', '')} {s.get('note', '')}" for s in fallback]
    (DATA / "discovery_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save(sources: dict) -> None:
    (DATA / "sources.json").write_text(json.dumps(sources, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    write_report(sources)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="re-check companies already discovered")
    ap.add_argument("--only", help="comma-separated company ids")
    ap.add_argument("--segment", help="IB or PE only")
    args = ap.parse_args()

    companies = load_companies()
    seeds = load_json("seeds.json", {})
    overrides = load_json("overrides.json", {})
    sources = load_json("sources.json", {})
    todo = [c for c in companies
            if (args.all or c["id"] not in sources or not sources[c["id"]].get("system") or c["id"] in overrides)
            and (not args.only or c["id"] in args.only.split(","))
            and (not args.segment or c["segment"] == args.segment)]
    print(f"Discovering {len(todo)} of {len(companies)} companies", flush=True)
    http = Http(min_gap=0.3)
    started = time.monotonic()
    budget = float(os.environ.get("BUDGET_MINUTES", "12")) * 60
    # Plain web requests run in parallel; the screenless browser only works on
    # one thread, so pages that need it are handled afterwards, one by one.
    # Anything not reached within the time budget is picked up by the next run.
    def one(c):
        if time.monotonic() - started > budget * 0.6:
            return None
        return discover_one(c, seeds, overrides, http)

    later = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        for result in pool.map(one, todo):
            if result is None:
                continue
            if result.pop("needs_browser", False):
                later.append(result)
                continue
            sources[result["id"]] = result
            print(f"  {result['name']}: {result.get('system') or '-'} ({result['how']})", flush=True)
    save(sources)  # keep what we have before the slower browser step
    for result in later:
        if time.monotonic() - started > budget:
            print(f"  {result['name']}: left for the next run (time budget)", flush=True)
            continue
        try:
            final, html = rendered_html(result["careers_url"])
            found = detect(final, html)
            system, params = found if found else ("browser", {"url": final})
            note = "" if found else "no known hiring system found; reading the page in the browser"
        except Exception as e:  # noqa: BLE001
            system, params, note = "browser", {"url": result["careers_url"]}, f"browser failed: {e.__class__.__name__}"
        result.update({"system": system, "params": params, "note": note})
        sources[result["id"]] = result
        print(f"  {result['name']}: {system} (careers page, browser)", flush=True)
    print(f"Finished in {round((time.monotonic() - started) / 60, 1)} minutes", flush=True)
    save(sources)
    try:
        from .readers.browser import close
        close()
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
