from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Job


def to_date(value) -> str:
    """Turn the many date formats hiring systems use into YYYY-MM-DD."""
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        secs = value / 1000 if value > 10**11 else value
        return dt.datetime.fromtimestamp(secs, dt.timezone.utc).date().isoformat()
    s = str(value).strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%d/%m/%Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def links_from_html(html: str, base_url: str, must_contain: str | list[str]) -> list[Job]:
    """Collect job links from a plain HTML list page."""
    needles = [must_contain] if isinstance(must_contain, str) else must_contain
    soup = BeautifulSoup(html, "html.parser")
    jobs: dict[str, Job] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not any(n in href for n in needles):
            continue
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title or len(title) < 4:
            continue
        url = urljoin(base_url, href)
        row = a.find_parent(["tr", "li", "article", "div"])
        location = ""
        if row is not None:
            loc_el = row.find(class_=re.compile("location|city", re.I))
            if loc_el is not None and loc_el is not a:
                location = " ".join(loc_el.get_text(" ", strip=True).split())
        jobs.setdefault(url, Job(title=title, url=url, location=location))
    return list(jobs.values())
