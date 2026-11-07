"""Fallback for careers sites that only show jobs after running JavaScript
(Taleo, custom-built sites, anything without a known feed). It opens the
page in Chrome without a screen and copies the job links it can see."""
from __future__ import annotations

import re
import threading
from urllib.parse import urljoin

from ..filters import EARLY
from ..http import USER_AGENT, Blocked
from ..models import Job

_lock = threading.Lock()
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
    url = p["url"]
    if not http.allowed(url):
        raise Blocked(url)
    link_hint = p.get("link_contains")
    with _lock:  # Playwright's sync API is not thread-safe: one page at a time
        page = _browser().new_page(user_agent=USER_AGENT)
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
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
        if not link_hint and not EARLY.search(text):
            continue
        full = urljoin(url, href)
        out.setdefault(full, Job(title=re.sub(r"\s+", " ", text), url=full))
    return list(out.values())
