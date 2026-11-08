"""Probe: open careers pages in the screenless browser and write down every
job-system address the page uses (links and background requests). A person
(or Claude) reads data/probe.json to work out the right settings for a firm.

Run by hand:  python -m robot.probe  [--only id1,id2] [--urls extra.json]
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from .http import USER_AGENT

DATA = Path(__file__).resolve().parent.parent / "data"
ATS = re.compile(
    r"tal\.net|myworkdayjobs|oraclecloud|greenhouse\.io|avature|successfactors|jobs2web|eightfold|phenom|icims|"
    r"smartrecruiters|workable|lever\.co|taleo|brassring|pageuppeople|ashbyhq|jobvite|teamtailor|recruitee|pinpointhq|"
    r"cezanne|bamboohr|personio|beapplied|hirehive|jobtrain|oleeo|tribepad|talentlink|kenexa|csod|cvmail|"
    r"graphql|/api/|/services/|search-jobs|jobsearch|job-search|/jobs\b|/vacanc|/careers/job|requisition|apply",
    re.I,
)
SKIP = re.compile(r"\.(png|jpe?g|gif|svg|webp|woff2?|ttf|css|ico)(\?|$)|google|doubleclick|facebook|linkedin\.com/(?!jobs)|"
                  r"hotjar|onetrust|cookielaw|analytics|tiktok|twitter|youtube|bing\.com|adobedtm|demdex|newrelic|"
                  r"clarity\.ms|qualtrics|optimizely", re.I)


def probe(url: str, browser) -> dict:
    page = browser.new_page(user_agent=USER_AGENT)
    requests: list[str] = []
    page.on("request", lambda r: requests.append(r.url))
    out = {"url": url}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        for _ in range(2):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(700)
        links = page.eval_on_selector_all(
            "a[href],iframe[src],form[action]",
            "els => els.map(e => [e.href || e.src || e.action || '', (e.innerText || '').trim().slice(0, 80)])",
        )
        out["final"] = page.url
        out["title"] = page.title()[:100]
        out["links"] = sorted({f"{h} | {t}" for h, t in links if h and ATS.search(h) and not SKIP.search(h)})[:40]
        out["requests"] = sorted({r.split("#")[0][:220] for r in requests if ATS.search(r) and not SKIP.search(r)})[:40]
        out["hosts"] = sorted({r.split("/")[2] for r in requests if "://" in r and not SKIP.search(r)})[:40]
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{e.__class__.__name__}: {str(e)[:200]}"
    finally:
        page.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated company ids (default: all IB/PE firms with a careers link)")
    ap.add_argument("--urls", help="JSON file of {name: url} to probe as well")
    ap.add_argument("--shard", default="1/1", help="i/n: probe only every n-th page, starting at i (runs in parallel)")
    args = ap.parse_args()
    seeds = json.loads((DATA / "seeds.json").read_text(encoding="utf-8"))
    targets = dict(seeds)
    if args.urls:
        targets.update(json.loads(Path(args.urls).read_text(encoding="utf-8")))
    if args.only:
        targets = {k: v for k, v in targets.items() if k in args.only.split(",")}
    i, n = (int(x) for x in args.shard.split("/"))
    targets = {k: v for j, (k, v) in enumerate(sorted(targets.items())) if j % n == i - 1}
    from playwright.sync_api import sync_playwright

    started = time.monotonic()
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, url in targets.items():
            if time.monotonic() - started > 14 * 60:
                break
            results[name] = probe(url, browser)
            r = results[name]
            found = sorted({re.sub(r"[?#].*", "", x.split(" | ")[0])[:160] for x in r.get("links", []) + r.get("requests", [])})
            print("PROBE " + json.dumps({"id": name, "final": r.get("final", ""), "error": r.get("error", ""), "title": r.get("title", ""),
                                        "found": found[:25]}, ensure_ascii=False), flush=True)
        browser.close()
    (DATA / f"probe-{i}.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
