from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict


@dataclass
class Job:
    """One job posting as read from a hiring system."""

    title: str
    url: str
    location: str = ""
    posted: str = ""  # YYYY-MM-DD when the system gives one
    external_id: str = ""
    extra: dict = field(default_factory=dict)

    def key(self, company_id: str) -> str:
        base = f"{company_id}|{self.external_id or self.url or self.title}".lower()
        return "j-" + hashlib.sha1(base.encode()).hexdigest()[:14]

    def to_dict(self) -> dict:
        return asdict(self)
