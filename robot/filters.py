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
    r"associate director|executive director|chief|summer associate|mba|apprentice\w*)\b",
    re.I,
)
EARLY = re.compile(
    r"\bintern(s|ship|ships)?\b|summer analyst|graduate|spring week|spring insight|insight (day|week|programme|program|event)|"
    r"off[- ]?cycle|placement|work experience|"
    r"early careers?|campus|analyst program|analyst programme|new analyst|entry[- ]level|student|"
    r"\b20(2[6-9])\b.*\banalyst\b|\banalyst\b.*\b20(2[6-9])\b",
    re.I,
)
LONDON = re.compile(r"\blondon\b|\bcanary wharf\b|\bcity of london\b", re.I)
UK_ONLY = re.compile(r"^(uk|united kingdom|great britain|england|gb)$", re.I)


# Jobs at banks that are not investment banking / private equity (scope: advisory and financing).
OFF_SCOPE = re.compile(
    r"technolog|software|engineer|developer|\bdata\b|cyber|\bIT\b|digital|\bAI\b|machine learning|quant|"
    r"operations|\bops\b|sales|trading|trader|(?<!capital )\bmarkets\b|research|wealth|private bank|asset management|"
    r"audit|assurance|\btax\b|risk|compliance|legal|human resources|\bHR\b|marketing|procurement|"
    r"treasury|payments|retail|branch|customer|actuar|pension|insurance|consulting|accountan",
    re.I,
)
# Words that only appear on articles and menus, never on job adverts.
NOT_A_JOB = re.compile(r"^(insights?|news|blog|events?|our people|meet|read more|learn more|life at|faq|how we hire|"
                       r"diversity|stories|podcast|report)\b|\b(insights?|article|webinar|podcast|newsletter|report \d{4})$", re.I)
OTHER_CITY = re.compile(
    r"new york|\bnyc\b|hong kong|singapore|dubai|abu dhabi|riyadh|doha|houston|chicago|boston|san francisco|los angeles|"
    r"washington|toronto|montreal|sydney|melbourne|mumbai|bangalore|bengaluru|tokyo|shanghai|beijing|paris|frankfurt|"
    r"madrid|milan|amsterdam|zurich|geneva|luxembourg|stockholm|dublin|edinburgh|glasgow|aberdeen|manchester|birmingham|"
    r"leeds|bristol|belfast|cardiff|stoke|reading|cambridge|oxford|newcastle|nottingham|sheffield|southampton|liverpool|milton keynes|\bemea\b(?!.*london)|\bapac\b|americas|\bus\b|\busa\b",
    re.I,
)


# A link on a careers web page counts as a job only if it names something specific:
# a year, an analyst role or a deal team. "Graduates" or "Early careers" are menu links.
JOB_LINK = re.compile(
    r"\b20(2[6-9])\b|analyst|investment bank|corporate finance|financial advisory|\bm&a\b|mergers|private equity|"
    r"capital markets|leveraged finance|restructuring|spring (week|insight)|insight (week|programme|program|day)|off[- ]?cycle",
    re.I,
)
NOT_A_PAGE_FOR_ONE_JOB = re.compile(r"faqs?\b|application process|how to apply|compare|view all|overview", re.I)


def is_job_link(text: str) -> bool:
    return bool(JOB_LINK.search(text)) and not NOT_A_PAGE_FOR_ONE_JOB.search(text) and len(text.split()) >= 3


def is_entry_level(title: str) -> bool:
    if not EARLY.search(title) or NOT_A_JOB.search(title.strip()):
        return False
    # "Graduate Associate" is fine; "Senior Associate" is not.
    return not SENIOR.search(title)


def in_scope(title: str) -> bool:
    """Investment banking / private equity work, not other jobs at the same firm."""
    return not OFF_SCOPE.search(title)


def is_london(location: str, title: str = "") -> bool | None:
    """True / False when we can tell, None when the system gave no location."""
    text = f"{location} {title}".strip()
    if LONDON.search(text):
        return True
    if OTHER_CITY.search(text):
        return False
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
