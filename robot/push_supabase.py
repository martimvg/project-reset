"""Copy the robot's results into the website's database (Supabase).

Runs on GitHub after every check, but only when two secrets are set in the repository:
SUPABASE_URL and SUPABASE_SERVICE_KEY. Without them it does nothing.
It sends: every role (robot, hand-checked, found on job boards), every firm with its careers link,
and the robot's summary numbers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def rows_for_db() -> tuple[list[dict], list[dict], dict]:
    site = json.loads((ROOT / "site/openings.json").read_text(encoding="utf-8"))
    openings = []
    for r in site["openings"]:
        openings.append({
            "id": r["id"], "firm": r["firm"], "title": r["title"], "url": r.get("url", ""), "location": r.get("location", "London"),
            "category": r.get("category", "Investment Banking"), "area": r.get("area", ""), "level": r.get("level", ""),
            "posted": r.get("posted", "") or "", "first_seen": r.get("firstSeen", ""), "deadline": r.get("deadline", "") or "",
            "rolling": bool(r.get("rolling")), "status": r.get("status", "open"), "source": "found" if r.get("manual") else "robot",
            "found_on": r.get("foundOn", ""), "note": r.get("note", ""), "unconfirmed": bool(r.get("unconfirmed")),
            "apply": r.get("apply") or {"method": "web"},
        })
    hand_file = ROOT / "data/hand_checked.json"
    for r in (json.loads(hand_file.read_text(encoding="utf-8")) if hand_file.exists() else []):
        openings.append({
            "id": r["id"], "firm": r.get("firm", ""), "title": r.get("title", ""), "url": r.get("url", ""), "location": r.get("location", "London"),
            "category": r.get("category", "Investment Banking"), "area": r.get("area", ""), "level": r.get("level", ""),
            "posted": r.get("posted", "") or "", "first_seen": r.get("firstSeen", ""), "last_checked": r.get("lastChecked", ""),
            "deadline": r.get("deadline", "") or "", "rolling": bool(r.get("rolling")), "status": r.get("status", "open"),
            "source": "hand", "apply": r.get("apply") or {"method": "web"},
        })
    firms = [{"id": f["id"], "name": f["name"], "sector": f.get("sector", ""), "category": f.get("category", ""), "url": f.get("url", ""),
              "readable": bool(f.get("readable")), "last_read": f.get("lastRead", "")} for f in site.get("firms", [])]
    return openings, firms, site.get("meta", {})


def main() -> None:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Supabase secrets not set: skipping the database update.")
        return
    openings, firms, meta = rows_for_db()
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(base_url=url.rstrip("/") + "/rest/v1", headers=headers, timeout=60) as c:
        for i in range(0, len(openings), 500):
            c.post("/openings", content=json.dumps(openings[i:i + 500])).raise_for_status()
        c.post("/firms", content=json.dumps(firms)).raise_for_status()
        c.post("/meta", content=json.dumps([{"key": "robot", "value": meta}])).raise_for_status()
    print(f"Database updated: {len(openings)} roles, {len(firms)} firms.")


if __name__ == "__main__":
    main()
