"""Rules that decide whether a posting is an entry-level London role and
which programme type it is. Plain keyword rules: no AI needed."""
from __future__ import annotations

import re

LEVELS = {
    "Spring Insight": r"spring (week|insight|programme|program)|insight (day|week|programme|program|event)|discovery (day|week|programme)|work experience|discover\b|open day",
    "Industrial Placement": r"industrial placement|placement year|sandwich placement|year[- ]long placement|12[- ]month placement|\bplacement\b",
    "Off Cycle Internship": r"off[- ]?cycle|seasonal internship|long[- ]term internship|(6|six|12|twelve)[- ]month internship|winter internship|spring internship|autumn internship|january start|september start",
    "Graduate / Entry Level": r"graduate|full[- ]time analyst|analyst (program|programme)|new analyst|entry[- ]level|early careers? analyst",
    "Summer Internship": r"summer|intern\b|internship|interns\b|summer analyst",
}

SENIOR = re.compile(
    r"\b(vice president|vp\b|director|managing director|\bmd\b|head of|principal|senior|lead\b|manager|partner\b|experienced|"
    r"associate director|executive director|chief)\b",
    re.I,
)
EARLY = re.compile(
    r"intern|internship|summer analyst|graduate|spring week|insight|off[- ]?cycle|placement|work experience|"
    r"early careers?|campus|apprentice|analyst program|analyst programme|new analyst|entry[- ]level|student|"
    r"\b20(2[6-9])\b.*\banalyst\b|\banalyst\b.*\b20(2[6-9])\b",
    re.I,
)
LONDON = re.compile(r"\blondon\b|\bcanary wharf\b|\bcity of london\b", re.I)
UK_ONLY = re.compile(r"^(uk|united kingdom|great britain|england|gb)$", re.I)


def is_entry_level(title: str) -> bool:
    if not EARLY.search(title):
        return False
    # "Graduate Associate" is fine; "Senior Associate" is not.
    return not SENIOR.search(title)


def is_london(location: str, title: str = "") -> bool | None:
    """True / False when we can tell, None when the system gave no location."""
    text = f"{location} {title}".strip()
    if LONDON.search(text):
        return True
    loc = location.strip()
    if not loc:
        return None
    if UK_ONLY.match(loc):
        return None  # UK-wide: keep, flag for a person to check
    return False


def programme_type(title: str) -> str:
    t = title.lower()
    for level, pattern in LEVELS.items():
        if re.search(pattern, t):
            return level
    return "Summer Internship" if "analyst" in t else "Graduate / Entry Level"


ENTRY_SEARCH_WORDS = ["intern", "graduate", "spring", "insight", "off-cycle", "placement", "summer analyst", "early careers"]
