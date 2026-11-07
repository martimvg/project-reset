"""Turn the robot's results into the list the website's Openings table reads
(site/openings.json)."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AREAS = [("restructur", "Restructuring"), ("insolvency", "Restructuring"), ("leveraged", "Leveraged Finance"),
         ("debt", "Debt Advisory / DCM"), ("dcm", "Debt Advisory / DCM"), ("capital markets", "Capital Markets"),
         ("ecm", "Capital Markets"), ("sponsor", "Financial Sponsors"), ("fig", "FIG"), ("real estate", "Real Estate"),
         ("m&a", "M&A"), ("mergers", "M&A"), ("corporate finance", "Corporate Finance"), ("transaction", "Transaction Services"),
         ("private equity", "Private Equity"), ("infrastructure", "Infrastructure"), ("credit", "Private Credit"),
         ("coverage", "Coverage"), ("advisory", "Advisory")]


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
        rows.append({
            "id": key, "firm": r["company"], "title": r["title"], "url": r["url"],
            "location": "London" if r.get("location_checked") else (r.get("location") or "Not stated"),
            "category": "Private Equity" if r["segment"] == "PE" else "Investment Banking",
            "area": area(r["title"]), "level": r.get("programme", ""), "posted": r.get("posted", ""),
            "firstSeen": (r.get("first_seen") or "")[:10], "deadline": "", "rolling": False,
            "status": r.get("status", "open"),
        })
    in_scope = [s for s in sources.values() if s.get("segment") in ("IB", "PE")]
    meta = {
        "lastRun": max((r.get("last_seen", "") for r in openings.values()), default=""),
        "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "firmsTracked": len(in_scope),
        "firmsReadable": sum(1 for s in in_scope if s.get("system") and health.get(s["id"], {}).get("failures", 1) == 0),
        "seededOn": min((r["firstSeen"] for r in rows if r["firstSeen"]), default=""),
    }
    out = ROOT / "site"
    out.mkdir(exist_ok=True)
    (out / "openings.json").write_text(json.dumps({"meta": meta, "openings": rows}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} roles written to site/openings.json")


if __name__ == "__main__":
    main()
