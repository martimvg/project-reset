"""Polite web access: one client, a pause between calls to the same site,
and a check of each site's robots.txt (the file where a site says which
pages automated tools may read)."""
from __future__ import annotations

import threading
import time
import urllib.robotparser
from urllib.parse import urlsplit

import httpx

USER_AGENT = "ProjectResetBot/0.1 (+https://github.com/martimvg/project-reset)"


class Blocked(Exception):
    """The site's robots.txt asks tools like ours not to read this page."""


class Http:
    def __init__(self, min_gap: float = 1.0, timeout: float = 25.0):
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )
        self.min_gap = min_gap
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._lock = threading.Lock()
        self._host_locks: dict[str, threading.Lock] = {}

    # --- etiquette -------------------------------------------------------
    def _host_lock(self, host: str) -> threading.Lock:
        with self._lock:
            return self._host_locks.setdefault(host, threading.Lock())

    def _wait_turn(self, host: str) -> None:
        last = self._last.get(host, 0.0)
        gap = time.monotonic() - last
        if gap < self.min_gap:
            time.sleep(self.min_gap - gap)
        self._last[host] = time.monotonic()

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.client.get(origin + "/robots.txt", timeout=10)
                if r.status_code >= 400:
                    rp = None  # no robots file: everything allowed
                else:
                    rp.parse(r.text.splitlines())
            except httpx.HTTPError:
                rp = None
            self._robots[origin] = rp
        rp = self._robots[origin]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def _request(self, method: str, url: str, **kw) -> httpx.Response:
        host = urlsplit(url).netloc
        with self._host_lock(host):
            if not self.allowed(url):
                raise Blocked(url)
            self._wait_turn(host)
            r = self.client.request(method, url, **kw)
        r.raise_for_status()
        return r

    # --- the three calls readers use ------------------------------------
    def get_json(self, url: str, params: dict | None = None):
        return self._request("GET", url, params=params, headers={"Accept": "application/json"}).json()

    def post_json(self, url: str, payload: dict, params: dict | None = None):
        return self._request(
            "POST", url, json=payload, params=params,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ).json()

    def get_text(self, url: str, params: dict | None = None) -> str:
        return self._request("GET", url, params=params).text

    def final_url_and_text(self, url: str) -> tuple[str, str]:
        r = self._request("GET", url)
        return str(r.url), r.text
