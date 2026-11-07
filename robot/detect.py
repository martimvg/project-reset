"""Work out which hiring system a careers page uses, from its address and
the links and code inside the page."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

# (system, pattern over URL or HTML, function turning the match into settings)
URL_RULES = [
    ("workday", r"https?://(?P<host>(?P<tenant>[\w-]+)\.wd\d+\.myworkdayjobs\.com)/(?:[a-zA-Z]{2}-[a-zA-Z]{2}/)?(?P<site>(?![a-zA-Z]{2}-[a-zA-Z]{2}\b)[\w-]+)",
     lambda m: {"host": m["host"], "tenant": m["tenant"], "site": m["site"]}),
    ("oracle", r"https?://(?P<host>[\w.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[\w-]+/sites/(?P<site>[\w-]+)",
     lambda m: {"host": m["host"], "site": m["site"]}),
    ("greenhouse", r"https?://(?:job-)?boards(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?(?P<board>[\w-]+)",
     lambda m: {"board": m["board"]}),
    ("greenhouse", r"boards-api\.greenhouse\.io/v1/boards/(?P<board>[\w-]+)", lambda m: {"board": m["board"]}),
    ("lever", r"https?://jobs\.(?P<eu>eu\.)?lever\.co/(?P<site>[\w-]+)",
     lambda m: {"site": m["site"], "eu": bool(m["eu"])}),
    ("ashby", r"https?://jobs\.ashbyhq\.com/(?P<board>[\w.-]+)", lambda m: {"board": m["board"]}),
    ("smartrecruiters", r"https?://(?:jobs|careers)\.smartrecruiters\.com/(?!ni/|oneclick)(?P<company>[\w-]+)",
     lambda m: {"company": m["company"]}),
    ("workable", r"https?://apply\.workable\.com/(?P<account>[\w-]+)", lambda m: {"account": m["account"]}),
    ("recruitee", r"https?://(?P<company>[\w-]+)\.recruitee\.com", lambda m: {"company": m["company"]}),
    ("pinpoint", r"https?://(?P<company>[\w-]+)\.pinpointhq\.com", lambda m: {"company": m["company"]}),
    ("bamboohr", r"https?://(?P<company>[\w-]+)\.bamboohr\.com", lambda m: {"company": m["company"]}),
    ("personio", r"https?://(?P<host>(?P<company>[\w-]+)\.jobs\.personio\.(?:de|com))", lambda m: {"host": m["host"], "company": m["company"]}),
    ("teamtailor", r"https?://(?P<host>(?!www\.)[\w-]+\.teamtailor\.com)", lambda m: {"feed": f"https://{m['host']}/jobs.rss"}),
    ("eightfold", r"https?://(?P<host>[\w-]+\.eightfold\.ai)/careers\?[^\"'\s]*domain=(?P<domain>[\w.-]+)",
     lambda m: {"host": m["host"], "domain": m["domain"]}),
    ("icims", r"https?://(?P<host>[\w-]+\.icims\.com)", lambda m: {"host": m["host"]}),
    ("avature", r"https?://(?P<host>[\w.-]+\.avature\.net)(?P<path>/[\w-]+)?/(?:SearchJobs|JobDetail)",
     lambda m: {"host": m["host"], "path": m["path"] or ""}),
    ("oleeo", r"(?P<url>https?://[\w.-]+\.tal\.net/vx/[^\"'\s<>]*?/candidate/(?:so/pm/\d+/pl/\d+|jobboard/vacancy/\d+/adv)/?)",
     lambda m: {"url": m["url"]}),
    ("jobvite", r"https?://jobs\.jobvite\.com/(?P<company>[\w-]+)", lambda m: {"company": m["company"]}),
    ("taleo", r"https?://(?P<host>[\w-]+\.taleo\.net)[^\"'\s<>]*", lambda m: {"url": m.group(0)}),
]

HTML_HINTS = [
    ("successfactors", r"/services/rss/job/|jobs2web|rmk-map|successfactors"),
    ("phenom", r"phApp\.ddo|phenompeople|cdn\.phenompeople\.com"),
    ("radancy", r"tbcdn\.talentbrew\.com|radancy|/search-jobs/"),
]


def detect(final_url: str, html: str = "") -> tuple[str, dict] | None:
    """Return (system, settings) or None if the page uses nothing we recognise."""
    # 1) the page address itself
    for system, pattern, make in URL_RULES:
        m = re.search(pattern, final_url)
        if m:
            return _finish(system, make(m), final_url)
    # 2) a known hiring system linked or embedded inside the page
    for system, pattern, make in URL_RULES:
        m = re.search(pattern, html or "")
        if m:
            return _finish(system, make(m), final_url)
    # 3) tell-tale code of systems that run on the company's own address
    for system, pattern in HTML_HINTS:
        if re.search(pattern, html or "", re.I):
            host = urlsplit(final_url).netloc
            if system == "phenom":
                m = re.search(r"https?://[\w.-]+/([a-z]+/[a-z]{2})/", final_url)
                return "phenom", {"host": host, "locale": m.group(1) if m else "global/en"}
            return system, {"host": host}
    return None


def _finish(system: str, settings: dict, final_url: str):
    if system == "teamtailor":
        return "rss", settings
    if system == "taleo":
        return "browser", {"url": settings["url"]}
    return system, settings
