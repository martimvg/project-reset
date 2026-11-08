"""Turn the robot's results into the list the website's Openings table reads
(site/openings.json)."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .filters import in_scope as ib_pe_work, is_entry_level, is_london, programme_type

ROOT = Path(__file__).resolve().parent.parent
AREAS = [("restructur", "Restructuring"), ("insolvency", "Restructuring"), ("leveraged", "Leveraged Finance"),
         ("debt", "Debt Advisory / DCM"), ("dcm", "Debt Advisory / DCM"), ("capital markets", "Capital Markets"),
         ("ecm", "Capital Markets"), ("sponsor", "Financial Sponsors"), ("fig", "FIG"), ("real estate", "Real Estate"),
         ("m&a", "M&A"), ("mergers", "M&A"), ("corporate finance", "Corporate Finance"), ("transaction", "Transaction Services"),
         ("private equity", "Private Equity"), ("infrastructure", "Infrastructure"), ("credit", "Private Credit"),
         ("coverage", "Coverage"), ("advisory", "Advisory")]


def ats_link(system: str, p: dict) -> str:
    """A page a person can open for a hiring system the robot reads."""
    if p.get("url") or p.get("urls"):
        return p.get("url") or p["urls"][0]
    return {
        "workday": lambda: f"https://{p['host']}/{p['site']}",
        "oracle": lambda: f"https://{p['host']}/hcmUI/CandidateExperience/en/sites/{p['site']}",
        "greenhouse": lambda: f"https://job-boards.greenhouse.io/{p['board']}",
        "lever": lambda: f"https://jobs.{'eu.' if p.get('eu') else ''}lever.co/{p['site']}",
        "ashby": lambda: f"https://jobs.ashbyhq.com/{p['board']}",
        "smartrecruiters": lambda: f"https://jobs.smartrecruiters.com/{p['company']}",
        "workable": lambda: f"https://apply.workable.com/{p['account']}",
        "recruitee": lambda: f"https://{p['company']}.recruitee.com",
        "pinpoint": lambda: f"https://{p['company']}.pinpointhq.com",
        "bamboohr": lambda: f"https://{p['company']}.bamboohr.com/careers",
        "personio": lambda: f"https://{p['host']}",
        "rss": lambda: p["feed"].replace("/jobs.rss", "/jobs"),
        "avature": lambda: f"https://{p['host']}{p.get('path', '')}/SearchJobs",
        "icims": lambda: f"https://{p['host']}/jobs/search",
        "phenom": lambda: f"https://{p['host']}",
        "successfactors": lambda: f"https://{p['host']}",
        "radancy": lambda: f"https://{p['host']}",
    }.get(system, lambda: "")()


def area(title: str) -> str:
    t = title.lower()
    for key, name in AREAS:
        if key in t:
            return name
    return ""


def main() -> None:
    openings = json.loads((ROOT / "data/openings.json").read_text(encoding="utf-8"))
    health = json.loads((ROOT / "data/health.json").read_text(encoding="utf-8")) if (ROOT / "data/health.json").exists() else {}
    sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
    rows = []
    for key, r in openings.items():
        if r.get("segment") not in ("IB", "PE"):
            continue
        # apply today's rules to older records too
        loc = "" if r.get("location") in ("", "Not stated") else r.get("location", "")
        if not (is_entry_level(r["title"]) and ib_pe_work(r["title"]) and is_london(loc, r["title"]) is not False):
            continue
        rows.append({
            "id": key, "firm": r["company"], "title": r["title"], "url": r["url"],
            "location": "London" if r.get("location_checked") else (r.get("location") or "Not stated"),
            "category": "Private Equity" if r["segment"] == "PE" else "Investment Banking",
            "area": area(r["title"]), "level": programme_type(r["title"]), "posted": r.get("posted", ""),
            "firstSeen": (r.get("first_seen") or "")[:10], "deadline": "", "rolling": False,
            "status": r.get("status", "open"),
        })
    # Roles added by hand (for example ones you apply to by email): data/manual.json
    manual_file = ROOT / "data/manual.json"
    for m in (json.loads(manual_file.read_text(encoding="utf-8")) if manual_file.exists() else []):
        closes = m.get("deadline", "")
        status = "closed" if closes and closes < dt.date.today().isoformat() else m.get("status", "open")
        rows.append({"id": m["id"], "firm": m["firm"], "title": m["title"], "url": m.get("url", ""),
                     "location": m.get("location", "London"), "category": m.get("category", "Investment Banking"),
                     "area": area(m["title"]), "level": m["level"], "posted": m.get("posted", ""),
                     "firstSeen": m.get("added", ""), "deadline": closes, "rolling": m.get("rolling", False),
                     "status": status, "apply": m.get("apply", {"method": "web"}), "manual": True,
                     "unconfirmed": m.get("unconfirmed", False), "foundOn": m.get("found_on", ""), "note": m.get("note", "")})
    seen, unique = set(), []
    for r in sorted(rows, key=lambda r: r["status"] != "open"):  # keep the open copy
        k = (r["firm"], r["title"].lower())
        if k not in seen:
            seen.add(k)
            unique.append(r)
    rows = unique
    in_scope = [s for s in sources.values() if s.get("segment") in ("IB", "PE")]
    seeds = json.loads((ROOT / "data/seeds.json").read_text(encoding="utf-8"))
    firms = []
    for s in sorted(in_scope, key=lambda s: s["name"].lower()):
        h = health.get(s["id"], {})
        link = s.get("careers_url") or seeds.get(s["id"]) or (ats_link(s["system"], s.get("params") or {}) if s.get("system") else "")
        firms.append({"id": s["id"], "name": s["name"], "sector": s.get("sector", ""),
                      "category": "Private Equity" if s["segment"] == "PE" else "Investment Banking",
                      "url": link, "readable": bool(s.get("system")) and h.get("failures", 1) == 0,
                      "lastRead": h.get("last_ok", "")})
    meta = {
        "lastRun": max((r.get("last_seen", "") for r in openings.values()), default=""),
        "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "firmsTracked": len(in_scope),
        "firmsReadable": sum(1 for s in in_scope if s.get("system") and health.get(s["id"], {}).get("failures", 1) == 0),
        "seededOn": min((r["firstSeen"] for r in rows if r["firstSeen"] and not r.get("manual")), default=""),
    }
    out = ROOT / "site"
    out.mkdir(exist_ok=True)
    (out / "openings.json").write_text(json.dumps({"meta": meta, "openings": rows, "firms": firms}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} roles written to site/openings.json")


if __name__ == "__main__":
    main()
