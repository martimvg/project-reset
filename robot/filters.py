"""Rules that decide whether a posting is an entry-level London role and
which of the seven programme types it is. Plain keyword rules: no AI needed.

Each posting goes through four questions, in this order:
  1. Is it early-careers?          (is_entry_level)
  2. Is it IB / PE work?           (in_scope)
  3. Is it in London?              (is_london)
  4. Which programme type is it?   (programme_type)
"""
from __future__ import annotations

import re

# The seven tabs of the tracker. Checked top to bottom: the first match wins,
# so the most specific types come first (a "Year 12 work experience week" is
# Pre-Uni, not a Spring Insight; an "Insight Event" is a Spring Insight).
PROGRAMMES = [
    ("Pre-Uni", r"sixth form|year 1[0-3]\b|school leaver|a[- ]levels?|gcse|pre[- ]?uni|apprentice|"
                r"school students?|for schools"),
    ("Spring Insight", r"spring (week|insight|programme|program)|insight (day|days|week|programme|program|event|events)|"
                       r"discovery (day|week|programme|program)|first[- ]year (insight|programme|program|students?)|work experience|open day|spring into"),
    ("Events", r"open (house|evening)|coffee chats?|info(rmation)? session|webinar|masterclass|workshop|"
               r"discovery (series|session)|event series|networking|meet the (firm|team)|panel|launch event|"
               r"virtual event|\bevents?\b|challenge|competition|careers fair"),
    ("Industrial Placement", r"industrial placement|placement year|sandwich|year[- ]long placement|"
                             r"(12|twelve)[- ]month placement|\bplacement\b"),
    ("Off-Cycle Internship", r"off[- ]?cycle|seasonal internship|long[- ]term internship|(3|three|6|six)[- ]month internship|"
                             r"winter internship|autumn internship|january start|september start"),
    ("Graduate Programme", r"graduate|full[- ]time analyst|analyst (program|programme)|new analyst|entry[- ]level|"
                           r"early careers? analyst|final[- ]year"),
    ("Summer Internship", r"summer|\bintern(s|ship|ships)?\b|vacation scheme"),
]
PROGRAMME_NAMES = [name for name, _ in PROGRAMMES]

SENIOR = re.compile(
    r"\b(vice president|vp\b|director|managing director|\bmd\b|head of|principal|senior|lead\b|manager|partner\b|experienced|"
    r"associate director|executive director|chief|summer associate|mba)\b",
    re.I,
)
EARLY = re.compile(
    r"\bintern(s|ship|ships)?\b|summer analyst|graduate|spring week|spring insight|spring into|insight (day|days|week|programme|program|event)|"
    r"off[- ]?cycle|placement|work experience|vacation scheme|first[- ]year|"
    r"early careers?|campus|analyst program|analyst programme|new analyst|entry[- ]level|student|"
    r"sixth form|school leaver|apprentice|pre[- ]?uni|"
    r"open house|coffee chat|discovery (series|day|week)|info(rmation)? session|masterclass|webinar|"
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
    r"treasury|payments|retail|branch|customer|actuar|pension|insurance|consulting|accountan|"
    r"talent acquisition|recruit|governance|internal|disputes|investigations|forensic|communications|transformation|"
    r"business services|business banking|commercial banking|transaction banking|claims|underwriting|fund services",
    re.I,
)
# Words that only appear on articles and menus, never on job adverts.
NOT_A_JOB = re.compile(r"^(insights?|news|blog|our people|meet|read more|learn more|life at|faq|how we hire|"
                       r"diversity|stories|podcast|report)\b|\b(insights?|article|podcast|newsletter|report \d{4})$", re.I)
OTHER_CITY = re.compile(
    r"new york|\bnyc\b|hong kong|singapore|dubai|abu dhabi|riyadh|doha|houston|chicago|boston|san francisco|los angeles|"
    r"menlo park|washington|toronto|montreal|sydney|melbourne|mumbai|bangalore|bengaluru|tokyo|shanghai|beijing|paris|"
    r"frankfurt|madrid|milan|amsterdam|zurich|geneva|luxembourg|stockholm|dublin|edinburgh|glasgow|aberdeen|manchester|"
    r"birmingham|leeds|bristol|belfast|cardiff|stoke|reading|cambridge|oxford|newcastle|nottingham|sheffield|southampton|"
    r"liverpool|milton keynes|ashbourne|derby|san diego|cleveland|atlanta|dallas|charlotte|minneapolis|denver|miami|\bemea\b(?!.*london)|\bapac\b|americas|\bus\b|\busa\b|u\.s\.|"
    r"dartmouth|georgetown|\bduke\b|harvard|wharton|\bhbcu\b|veteran",  # US campus events
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


# "Cleveland, OH" or "Austin, TX": a US state code after a comma (capitals only).
US_STATE = re.compile(r",\s*(A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b")


def is_london(location: str, title: str = "") -> bool | None:
    """True / False when we can tell, None when the system gave no location."""
    text = f"{location} {title}".strip()
    if LONDON.search(text):
        return True
    if OTHER_CITY.search(text) or US_STATE.search(text):
        return False
    loc = location.strip()
    if not loc:
        return None
    if UK_ONLY.match(loc):
        return None  # UK-wide: keep, flag for a person to check
    return False


def programme_type(title: str) -> str:
    t = title.lower()
    for name, pattern in PROGRAMMES:
        if re.search(pattern, t):
            return name
    return "Summer Internship" if "analyst" in t else "Graduate Programme"


ENTRY_SEARCH_WORDS = ["intern", "graduate", "spring", "insight", "off-cycle", "placement", "summer analyst",
                      "early careers", "apprentice", "open house"]
