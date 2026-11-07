"""Hiring systems that publish a public job feed in a structured format.
Each reader gets the source's settings (`p`) and the polite web client."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from ..models import Job
from .common import to_date


def greenhouse(p, http):
    data = http.get_json(f"https://boards-api.greenhouse.io/v1/boards/{p['board']}/jobs")
    return [
        Job(title=j["title"], url=j["absolute_url"], location=(j.get("location") or {}).get("name", ""),
            posted=to_date(j.get("first_published") or j.get("updated_at")), external_id=str(j["id"]))
        for j in data.get("jobs", [])
    ]


def lever(p, http):
    host = "api.eu.lever.co" if p.get("eu") else "api.lever.co"
    data = http.get_json(f"https://{host}/v0/postings/{p['site']}", params={"mode": "json"})
    return [
        Job(title=j["text"], url=j["hostedUrl"], location=(j.get("categories") or {}).get("location", ""),
            posted=to_date(j.get("createdAt")), external_id=j["id"])
        for j in data
    ]


def ashby(p, http):
    data = http.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{p['board']}")
    return [
        Job(title=j["title"], url=j.get("jobUrl") or j.get("applyUrl", ""), location=j.get("location", ""),
            posted=to_date(j.get("publishedAt")), external_id=j.get("id", ""))
        for j in data.get("jobs", [])
    ]


def smartrecruiters(p, http):
    out, offset = [], 0
    while True:
        data = http.get_json(
            f"https://api.smartrecruiters.com/v1/companies/{p['company']}/postings",
            params={"limit": 100, "offset": offset},
        )
        for j in data.get("content", []):
            loc = j.get("location") or {}
            out.append(Job(
                title=j["name"], url=f"https://jobs.smartrecruiters.com/{p['company']}/{j['id']}",
                location=", ".join(x for x in [loc.get("city"), loc.get("country")] if x),
                posted=to_date(j.get("releasedDate")), external_id=str(j["id"]),
            ))
        offset += 100
        if offset >= data.get("totalFound", 0) or offset > 2000:
            return out


def workable(p, http):
    out, token = [], None
    for _ in range(20):
        body = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
        if token:
            body["token"] = token
        data = http.post_json(f"https://apply.workable.com/api/v3/accounts/{p['account']}/jobs", body)
        for j in data.get("results", []):
            loc = j.get("location") or {}
            out.append(Job(
                title=j["title"], url=f"https://apply.workable.com/{p['account']}/j/{j['shortcode']}/",
                location=", ".join(x for x in [loc.get("city"), loc.get("country")] if x),
                posted=to_date(j.get("published")), external_id=j["shortcode"],
            ))
        token = data.get("nextPage")
        if not token:
            return out
    return out


def recruitee(p, http):
    data = http.get_json(f"https://{p['company']}.recruitee.com/api/offers/")
    return [
        Job(title=j["title"], url=j.get("careers_url", ""),
            location=j.get("location") or ", ".join(x for x in [j.get("city"), j.get("country")] if x),
            posted=to_date(j.get("published_at")), external_id=str(j["id"]))
        for j in data.get("offers", [])
    ]


def pinpoint(p, http):
    data = http.get_json(f"https://{p['company']}.pinpointhq.com/postings.json")
    return [
        Job(title=j["title"], url=j.get("url", ""), location=(j.get("location") or {}).get("name", ""),
            external_id=str(j.get("id", "")))
        for j in data.get("data", [])
    ]


def bamboohr(p, http):
    data = http.get_json(f"https://{p['company']}.bamboohr.com/careers/list")
    out = []
    for j in data.get("result", []):
        loc = j.get("location") or {}
        out.append(Job(
            title=j.get("jobOpeningName", ""), url=f"https://{p['company']}.bamboohr.com/careers/{j['id']}",
            location=", ".join(x for x in [loc.get("city"), loc.get("state")] if x), external_id=str(j["id"]),
        ))
    return out


def personio(p, http):
    host = p.get("host") or f"{p['company']}.jobs.personio.de"
    root = ET.fromstring(http.get_text(f"https://{host}/xml"))
    out = []
    for pos in root.iter("position"):
        pid = (pos.findtext("id") or "").strip()
        out.append(Job(
            title=(pos.findtext("name") or "").strip(), url=f"https://{host}/job/{pid}",
            location=(pos.findtext("office") or "").strip(), posted=to_date(pos.findtext("createdAt")),
            external_id=pid,
        ))
    return out


def rss(p, http):
    """Any careers site that offers an RSS feed (Teamtailor, many others)."""
    root = ET.fromstring(http.get_text(p["feed"]))
    out = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        loc = ""
        for child in item:
            if child.tag.lower().endswith("location") or child.tag.lower().endswith("city"):
                loc = (child.text or "").strip()
        out.append(Job(title=(item.findtext("title") or "").strip(), url=link, location=loc,
                       posted=to_date(item.findtext("pubDate")), external_id=link))
    return out
