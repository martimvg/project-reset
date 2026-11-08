"""Large-company hiring systems. These have thousands of jobs, so each reader
searches for entry-level words instead of reading every posting."""
from __future__ import annotations

import datetime as dt
import json
import re

from ..filters import ENTRY_SEARCH_WORDS
from ..models import Job
from .apis import rss
from .common import links_from_html, to_date


def _dedupe(jobs: list[Job]) -> list[Job]:
    seen, out = set(), []
    for j in jobs:
        k = j.external_id or j.url
        if k and k not in seen:
            seen.add(k)
            out.append(j)
    return out


def _workday_posted(text: str) -> str:
    t = (text or "").lower()
    today = dt.date.today()
    if "today" in t:
        return today.isoformat()
    if "yesterday" in t:
        return (today - dt.timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\s+days? ago", t)
    if m and "+" not in t:
        return (today - dt.timedelta(days=int(m.group(1)))).isoformat()
    return ""


def workday(p, http):
    """Workday careers sites, e.g. https://{tenant}.wd3.myworkdayjobs.com/{site}."""
    base = f"https://{p['host']}/wday/cxs/{p['tenant']}/{p['site']}/jobs"
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        for page in range(10):  # up to 200 results per search word
            data = http.post_json(base, {"appliedFacets": p.get("facets", {}), "limit": 20,
                                          "offset": page * 20, "searchText": word})
            rows = data.get("jobPostings", [])
            for j in rows:
                path = j.get("externalPath", "")
                out.append(Job(title=j.get("title", ""), url=f"https://{p['host']}/{p['site']}{path}",
                               location=j.get("locationsText", ""), posted=_workday_posted(j.get("postedOn", "")),
                               external_id=path))
            if len(rows) < 20:
                break
    return _dedupe(out)


def oracle(p, http):
    """Oracle Recruiting Cloud ('Candidate Experience') sites, e.g. J.P. Morgan."""
    base = f"https://{p['host']}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        for offset in range(0, 500, 100):  # big banks list hundreds of student roles worldwide: read them all
            finder = (f"findReqs;siteNumber={p['site']},facetsList=NONE,limit=100,offset={offset},"
                      f'keyword="{word}",sortBy=POSTING_DATES_DESC')
            data = http.get_json(base, params={"onlyData": "true", "expand": "requisitionList.secondaryLocations",
                                               "finder": finder})
            page = [j for block in data.get("items", []) for j in block.get("requisitionList", [])]
            for j in page:
                out.append(Job(
                    title=j.get("Title", ""),
                    url=f"https://{p['host']}/hcmUI/CandidateExperience/en/sites/{p['site']}/job/{j.get('Id')}",
                    location=j.get("PrimaryLocation", ""), posted=to_date(j.get("PostedDate")),
                    external_id=str(j.get("Id", "")),
                ))
            if len(page) < 100:
                break
    return _dedupe(out)


def successfactors(p, http):
    """SAP SuccessFactors career sites: they publish an RSS feed per search."""
    locale = p.get("locale", "en_GB")
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        feed = f"https://{p['host']}/services/rss/job/?locale={locale}&keywords=({word})"
        for j in rss({"feed": feed}, http):
            m = re.match(r"(.*)\(([^()]*)\)\s*$", j.title)  # "Title (London, GB)"
            if m and not j.location:
                j.title, j.location = m.group(1).strip(), m.group(2).strip()
            out.append(j)
    return _dedupe(out)


def eightfold(p, http):
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        data = http.get_json(f"https://{p['host']}/api/apply/v2/jobs",
                             params={"domain": p["domain"], "start": 0, "num": 100, "query": word})
        for j in data.get("positions", []):
            out.append(Job(
                title=j.get("name", ""),
                url=j.get("canonicalPositionUrl") or f"https://{p['host']}/careers?pid={j.get('id')}&domain={p['domain']}",
                location=j.get("location", ""), posted=to_date(j.get("t_create")), external_id=str(j.get("id", "")),
            ))
    return _dedupe(out)


def _embedded_json(html: str, marker: str):
    i = html.find(marker)
    if i < 0:
        return None
    start = html.find("{", i)
    depth, in_str, esc = 0, False, False
    for k in range(start, len(html)):
        c = html[k]
        if in_str:
            esc = (c == "\\") and not esc
            if c == '"' and not esc:
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start:k + 1])
    return None


def phenom(p, http):
    """Phenom People careers sites: the job list is embedded in the page."""
    locale = p.get("locale", "global/en")
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        html = http.get_text(f"https://{p['host']}/{locale}/search-results", params={"keywords": word})
        ddo = _embedded_json(html, "phApp.ddo") or {}
        jobs = (((ddo.get("eagerLoadRefineSearch") or {}).get("data") or {}).get("jobs")) or []
        for j in jobs:
            seq = j.get("jobSeqNo") or j.get("jobId", "")
            out.append(Job(
                title=j.get("title", ""), url=j.get("applyUrl") or f"https://{p['host']}/{locale}/job/{seq}",
                location=j.get("location") or ", ".join(x for x in [j.get("city"), j.get("country")] if x),
                posted=to_date(j.get("postedDate")), external_id=str(seq),
            ))
    return _dedupe(out)


def avature(p, http):
    path = p.get("path", "/careers")
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        url = f"https://{p['host']}{path}/SearchJobs/"
        out += links_from_html(http.get_text(url, params={"search": word}), url, "/JobDetail/")
    return _dedupe(out)


def icims(p, http):
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        url = f"https://{p['host']}/jobs/search"
        html = http.get_text(url, params={"ss": 1, "searchKeyword": word, "in_iframe": 1})
        out += [j for j in links_from_html(html, url, "/jobs/") if "/job" in j.url and "search" not in j.url]
    return _dedupe(out)


def oleeo(p, http):
    """Oleeo (tal.net) vacancy boards, used by many UK banks and boutiques.
    Firms often have several boards (e.g. one for the US, one for Europe): pass "urls"."""
    out = []
    for url in p.get("urls") or [p["url"]]:
        out += links_from_html(http.get_text(url), url, "/opp/")
    return _dedupe(out)


def radancy(p, http):
    """Radancy (TalentBrew) careers sites, e.g. Barclays and Citi."""
    out = []
    for word in p.get("search_words", ENTRY_SEARCH_WORDS):
        url = f"https://{p['host']}/search-jobs/{word.replace(' ', '%20')}"
        out += links_from_html(http.get_text(url), url, "/job/")
    return _dedupe(out)


def jobvite(p, http):
    url = f"https://jobs.jobvite.com/{p['company']}/jobs"
    return _dedupe(links_from_html(http.get_text(url), url, "/job/"))
