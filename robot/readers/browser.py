"""Fallback for careers sites that only show jobs after running JavaScript
(Taleo, custom-built sites, anything without a known feed). It opens the
page in Chrome without a screen and copies the job links it can see."""
from __future__ import annotations

import re
import threading
from urllib.parse import urljoin

from ..filters import EARLY, NOT_A_JOB, is_job_link
from ..http import USER_AGENT, Blocked
from ..models import Job

_lock = threading.RLock()  # re-entrant: browser() holds it while _browser() starts Chrome
_state: dict = {}


def _browser():
    with _lock:
        if "browser" not in _state:
            from playwright.sync_api import sync_playwright

            pw = sync_playwright().start()
            _state["pw"] = pw
            _state["browser"] = pw.chromium.launch()
        return _state["browser"]


def close():
    with _lock:
        if "browser" in _state:
            _state["browser"].close()
            _state["pw"].stop()
            _state.clear()


def browser(p, http):
    """Pass "url", or "urls" for firms with several job boards."""
    out: dict[str, Job] = {}
    for url in p.get("urls") or [p["url"]]:
        for job in _one_page(url, p.get("link_contains"), http):
            out.setdefault(job.url, job)
    return list(out.values())


def _one_page(url, link_hint, http):
    if not http.allowed(url):
        raise Blocked(url)
    with _lock:  # called from the main thread only (see run.py)
        page = _browser().new_page(user_agent=USER_AGENT)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            for _ in range(3):  # load lazy lists
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(800)
            anchors = page.eval_on_selector_all(
                "a[href]", "els => els.map(a => [a.href, (a.innerText||'').trim()])"
            )
        finally:
            page.close()
    out: dict[str, Job] = {}
    for href, text in anchors:
        text = " ".join(text.split())
        if not text or len(text) > 200:
            continue
        if link_hint and link_hint not in href:
            continue
        if not link_hint and (not EARLY.search(text) or NOT_A_JOB.search(text) or not is_job_link(text)):
            continue
        full = urljoin(url, href)
        if not link_hint and re.search(r"/(insights?|news|blog|articles?|events?|media|press)/", full, re.I):
            continue
        out.setdefault(full, Job(title=re.sub(r"\s+", " ", text), url=full))
    return list(out.values())
