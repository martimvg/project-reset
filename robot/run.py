"""The regular check: read every known source, keep entry-level London roles,
and update data/openings.json and data/health.json.

New roles get a first_seen date; roles that disappear from a working source
are marked closed. Sources that fail three times in a row are reported, and
the run is marked as failed so GitHub emails the owner."""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .filters import is_entry_level, is_london, programme_type
from .http import Blocked, Http
from .readers import READERS

DATA = Path(__file__).resolve().parent.parent / "data"
BROKEN_AFTER = 3


def load(name, default):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def read_source(src: dict, http: Http):
    started = time.monotonic()
    try:
        jobs = READERS[src["system"]](src.get("params") or {}, http)
        return src, jobs, None, time.monotonic() - started
    except Blocked:
        return src, [], "robots.txt asks tools not to read this page", time.monotonic() - started
    except Exception as e:  # noqa: BLE001 - one broken site must not stop the rest
        detail = "".join(traceback.format_exception_only(type(e), e)).strip()
        return src, [], detail[:300], time.monotonic() - started


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    today = dt.date.today().isoformat()
    sources = {k: v for k, v in load("sources.json", {}).items() if v.get("system") in READERS}
    only = os.environ.get("ONLY")  # e.g. ONLY=barclays,lazard for a quick test
    if only:
        sources = {k: v for k, v in sources.items() if k in only.split(",")}
    openings = load("openings.json", {})
    health = load("health.json", {})
    http = Http(min_gap=1.0)

    new_roles, newly_broken = [], []
    # Plain web requests run in parallel; browser-based sources run one by one
    # on the main thread (the screenless browser can't be shared between threads).
    plain = [s for s in sources.values() if s["system"] != "browser"]
    in_browser = [s for s in sources.values() if s["system"] == "browser"]
    with ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "8"))) as pool:
        results = list(pool.map(lambda s: read_source(s, http), plain))
    results += [read_source(s, http) for s in in_browser]

    for src, jobs, error, seconds in results:
        cid = src["id"]
        h = health.get(cid, {"failures": 0})
        h.update({"system": src["system"]})
        if error:
            h["failures"] = h.get("failures", 0) + 1
            h["error"] = error
            if h["failures"] == BROKEN_AFTER:
                newly_broken.append((src["name"], src["system"], error))
            health[cid] = h
            continue
        h.update({"failures": 0, "error": "", "last_ok": today, "postings_read": len(jobs)})
        seen_now = set()
        kept = 0
        for job in jobs:
            if not job.title or not job.url or not is_entry_level(job.title):
                continue
            london = is_london(job.location, job.title)
            if london is False:
                continue
            key = job.key(cid)
            seen_now.add(key)
            kept += 1
            rec = openings.get(key)
            if rec is None:
                rec = {"company_id": cid, "company": src["name"], "sector": src.get("sector", ""),
                       "segment": src.get("segment", ""), "first_seen": now, "system": src["system"]}
                new_roles.append((src["name"], job.title, job.url))
            rec.update({"title": job.title, "url": job.url, "location": job.location or "Not stated",
                        "location_checked": london is True, "programme": programme_type(job.title),
                        "posted": job.posted or rec.get("posted", ""), "last_seen": today, "status": "open"})
            rec.pop("closed_on", None)
            openings[key] = rec
        h["entry_level_found"] = kept
        health[cid] = h
        # roles that vanished from a source that worked this time have closed
        for key, rec in openings.items():
            if rec["company_id"] == cid and rec.get("status") == "open" and key not in seen_now:
                rec["status"] = "closed"
                rec["closed_on"] = today

    save("openings.json", openings)
    save("health.json", health)

    ok = sum(1 for _, _, e, _ in results if not e)
    open_count = sum(1 for r in openings.values() if r.get("status") == "open")
    broken = sorted((v.get("failures", 0), k) for k, v in health.items() if v.get("failures", 0) >= BROKEN_AFTER)
    lines = [f"## Check at {now}", "",
             f"- Sources read: {ok} of {len(results)}",
             f"- Open entry-level London roles: {open_count}",
             f"- New this run: {len(new_roles)}",
             f"- Sources broken ({BROKEN_AFTER}+ failures in a row): {len(broken)}", ""]
    if new_roles:
        lines += ["### New roles", ""] + [f"- **{c}**: [{t}]({u})" for c, t, u in new_roles[:200]] + [""]
    if newly_broken:
        lines += ["### Newly broken sources", ""] + [f"- {n} ({s}): {e}" for n, s, e in newly_broken] + [""]
    summary = "\n".join(lines)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    alert = DATA / "alert.txt"
    if newly_broken:
        alert.write_text(summary, encoding="utf-8")
    elif alert.exists():
        alert.unlink()
    try:
        from .readers.browser import close
        close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
