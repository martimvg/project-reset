"""Offline tests: each reader is fed a small sample in the format its hiring
system publishes, so we know the parsing works before going live.
The live check on GitHub confirms the real sites."""
import json

import pytest

from robot import filters
from robot.detect import detect
from robot.readers import READERS


class FakeHttp:
    """Stands in for the web: returns a canned answer for each address."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def _match(self, url):
        self.calls.append(url)
        for part, answer in self.routes.items():
            if part in url:
                return answer
        raise AssertionError(f"unexpected address {url}")

    def get_json(self, url, params=None):
        return self._match(url)

    def post_json(self, url, payload, params=None):
        return self._match(url)

    def get_text(self, url, params=None):
        return self._match(url)

    def allowed(self, url):
        return True


def run(system, params, routes):
    return READERS[system](params, FakeHttp(routes))


def test_greenhouse():
    jobs = run("greenhouse", {"board": "acme"}, {"boards-api.greenhouse.io/v1/boards/acme/jobs": {"jobs": [
        {"id": 1, "title": "2027 Summer Analyst", "absolute_url": "https://x/1", "location": {"name": "London"},
         "updated_at": "2026-10-01T10:00:00-04:00"}]}})
    assert jobs[0].title == "2027 Summer Analyst" and jobs[0].location == "London" and jobs[0].posted == "2026-10-01"


def test_lever():
    jobs = run("lever", {"site": "acme"}, {"api.lever.co/v0/postings/acme": [
        {"id": "a", "text": "Off-Cycle Intern", "hostedUrl": "https://l/a", "categories": {"location": "London"},
         "createdAt": 1790000000000}]})
    assert jobs[0].url == "https://l/a" and jobs[0].posted.startswith("2026")


def test_ashby():
    jobs = run("ashby", {"board": "acme"}, {"posting-api/job-board/acme": {"jobs": [
        {"id": "z", "title": "Graduate Analyst", "location": "London", "jobUrl": "https://a/z", "publishedAt": "2026-09-30T00:00:00Z"}]}})
    assert jobs[0].external_id == "z"


def test_smartrecruiters_paginates():
    page = {"totalFound": 1, "content": [{"id": "9", "name": "Summer Intern", "location": {"city": "London", "country": "gb"},
                                          "releasedDate": "2026-10-02T09:00:00.000Z"}]}
    jobs = run("smartrecruiters", {"company": "Acme"}, {"api.smartrecruiters.com": page})
    assert jobs[0].url == "https://jobs.smartrecruiters.com/Acme/9" and jobs[0].location == "London, gb"


def test_workable():
    jobs = run("workable", {"account": "acme"}, {"apply.workable.com/api/v3/accounts/acme/jobs": {"results": [
        {"shortcode": "AB1", "title": "Analyst Intern", "location": {"city": "London", "country": "United Kingdom"},
         "published": "2026-10-03"}]}})
    assert jobs[0].url.endswith("/j/AB1/")


def test_recruitee_pinpoint_bamboo_personio():
    assert run("recruitee", {"company": "acme"}, {"acme.recruitee.com": {"offers": [
        {"id": 3, "title": "Intern", "careers_url": "https://r/3", "city": "London", "country": "UK"}]}})[0].location == "London, UK"
    assert run("pinpoint", {"company": "acme"}, {"acme.pinpointhq.com": {"data": [
        {"id": 4, "title": "Intern", "url": "https://p/4", "location": {"name": "London"}}]}})[0].url == "https://p/4"
    assert run("bamboohr", {"company": "acme"}, {"acme.bamboohr.com": {"result": [
        {"id": 5, "jobOpeningName": "Intern", "location": {"city": "London"}}]}})[0].url.endswith("/careers/5")
    xml = "<workzag-jobs><position><id>7</id><name>Intern</name><office>London</office></position></workzag-jobs>"
    assert run("personio", {"company": "acme"}, {"acme.jobs.personio.de/xml": xml})[0].url.endswith("/job/7")


def test_workday_searches_and_dedupes():
    data = {"total": 1, "jobPostings": [{"title": "2027 Summer Analyst Programme", "externalPath": "/job/London/Summer_R1",
                                         "locationsText": "London", "postedOn": "Posted 3 Days Ago"}]}
    jobs = run("workday", {"host": "acme.wd3.myworkdayjobs.com", "tenant": "acme", "site": "Campus"}, {"/wday/cxs/acme/Campus/jobs": data})
    assert len(jobs) == 1  # same posting found by several search words is kept once
    assert jobs[0].url == "https://acme.wd3.myworkdayjobs.com/Campus/job/London/Summer_R1" and jobs[0].posted


def test_oracle():
    data = {"items": [{"requisitionList": [{"Id": "210", "Title": "2027 Investment Banking Summer Analyst",
                                            "PrimaryLocation": "London, United Kingdom", "PostedDate": "2026-08-31"}]}]}
    jobs = run("oracle", {"host": "jpmc.fa.oraclecloud.com", "site": "CX_1001"}, {"recruitingCEJobRequisitions": data})
    assert jobs[0].url.endswith("/sites/CX_1001/job/210") and jobs[0].posted == "2026-08-31"


def test_successfactors_rss_splits_location():
    feed = ("<rss><channel><item><title>Graduate Programme 2027 (London, GB)</title><link>https://s/job/1</link>"
            "<pubDate>Mon, 05 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>")
    jobs = run("successfactors", {"host": "careers.acme.com"}, {"/services/rss/job/": feed})
    assert jobs[0].title == "Graduate Programme 2027" and jobs[0].location == "London, GB" and jobs[0].posted == "2026-10-05"


def test_eightfold():
    data = {"positions": [{"id": 11, "name": "Summer Intern", "location": "London, UK", "t_create": 1790000000}]}
    jobs = run("eightfold", {"host": "acme.eightfold.ai", "domain": "acme.com"}, {"/api/apply/v2/jobs": data})
    assert "pid=11" in jobs[0].url


def test_phenom_embedded_json():
    ddo = {"eagerLoadRefineSearch": {"data": {"jobs": [{"title": "Spring Insight Week", "jobSeqNo": "ACME1", "city": "London",
                                                         "country": "United Kingdom", "postedDate": "2026-10-10T00:00:00"}]}}}
    html = f"<script>phApp.ddo = {json.dumps(ddo)}; phApp.other = 1;</script>"
    jobs = run("phenom", {"host": "careers.acme.com", "locale": "global/en"}, {"/search-results": html})
    assert jobs[0].url.endswith("/global/en/job/ACME1") and jobs[0].location == "London, United Kingdom"


def test_html_boards():
    av = '<li><a href="/careers/JobDetail/Summer-Analyst/123">2027 Summer Analyst</a><span class="location">London</span></li>'
    assert run("avature", {"host": "acme.avature.net", "path": "/careers"}, {"SearchJobs": av})[0].location == "London"
    ic = '<div><a href="https://careers-acme.icims.com/jobs/55/graduate/job">Graduate Analyst</a></div>'
    assert run("icims", {"host": "careers-acme.icims.com"}, {"/jobs/search": ic})[0].title == "Graduate Analyst"
    ol = '<tr><td><a href="/vx/x/candidate/so/pm/1/pl/2/opp/391-2027-Summer-Analyst/en-GB">2027 Summer Analyst - London</a></td></tr>'
    assert len(run("oleeo", {"url": "https://acme.tal.net/vx/x/candidate/jobboard/vacancy/2/adv/"}, {"acme.tal.net": ol})) == 1
    jv = '<a href="/acme/job/oAbC">Off-Cycle Intern</a>'
    assert run("jobvite", {"company": "acme"}, {"jobs.jobvite.com/acme/jobs": jv})[0].url == "https://jobs.jobvite.com/acme/job/oAbC"
    rd = '<a href="/job/london/summer-internship/13015/995">Banking Summer Internship 2027</a>'
    assert run("radancy", {"host": "search.jobs.acme"}, {"/search-jobs/": rd})[0].url.startswith("https://search.jobs.acme/job/")


@pytest.mark.parametrize("url,system,key,value", [
    ("https://acme.wd3.myworkdayjobs.com/en-US/Campus/details/x", "workday", "site", "Campus"),
    ("https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions", "oracle", "site", "CX_1001"),
    ("https://job-boards.greenhouse.io/acme", "greenhouse", "board", "acme"),
    ("https://jobs.eu.lever.co/acme", "lever", "site", "acme"),
    ("https://jobs.ashbyhq.com/acme", "ashby", "board", "acme"),
    ("https://jobs.smartrecruiters.com/Acme1/123", "smartrecruiters", "company", "Acme1"),
    ("https://apply.workable.com/acme/", "workable", "account", "acme"),
    ("https://acme.teamtailor.com/jobs", "rss", "feed", "https://acme.teamtailor.com/jobs.rss"),
    ("https://acme.tal.net/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/candidate/jobboard/vacancy/2/adv/", "oleeo", "url", None),
    ("https://acme.taleo.net/careersection/2/jobsearch.ftl", "browser", "url", None),
])
def test_detect_by_address(url, system, key, value):
    found = detect(url, "")
    assert found and found[0] == system
    if value:
        assert found[1][key] == value


def test_detect_inside_page_and_hints():
    page = '<a href="https://boards.greenhouse.io/embed/job_board?for=acmeco">Jobs</a>'
    assert detect("https://acme.com/careers", page) == ("greenhouse", {"board": "acmeco"})
    assert detect("https://careers.acme.com/global/en/home", "<script>phApp.ddo = {}</script>")[0] == "phenom"
    assert detect("https://jobs.acme.com/", '<link href="https://tbcdn.talentbrew.com/x.css">')[0] == "radancy"
    assert detect("https://careers.acme.com/", '<a href="/services/rss/job/?locale=en_GB">RSS</a>')[0] == "successfactors"
    assert detect("https://acme.com/", "<p>hello</p>") is None


@pytest.mark.parametrize("title,ok", [
    ("2027 Summer Analyst Programme", True), ("Off-Cycle Internship - M&A", True), ("Spring Insight Week 2027", True),
    ("Graduate Associate, Deal Advisory", True), ("Vice President, M&A", False), ("Senior Associate, ECM", False),
    ("Analyst, Leveraged Finance", False), ("Industrial Placement 2027-28", True),
])
def test_entry_level(title, ok):
    assert filters.is_entry_level(title) is ok


def test_london_and_programme():
    assert filters.is_london("London, United Kingdom") is True
    assert filters.is_london("New York") is False
    assert filters.is_london("") is None and filters.is_london("United Kingdom") is None
    assert filters.programme_type("2027 Off-Cycle Analyst") == "Off-Cycle Internship"
    assert filters.programme_type("Spring Insight Programme") == "Spring Insight"
    assert filters.programme_type("Banking Graduate Programme 2027") == "Graduate Programme"
    assert filters.programme_type("Summer Internship 2027") == "Summer Internship"
    assert filters.programme_type("2027-2028 Industrial Placement") == "Industrial Placement"


def test_seven_programme_types():
    pt = filters.programme_type
    assert pt("Year 12 Work Experience Week") == "Pre-Uni"
    assert pt("Degree Apprenticeship – Investment Banking 2027") == "Pre-Uni"
    assert pt("2027 Spring Insight Week - Corporate Finance") == "Spring Insight"
    assert pt("RSM London Insight Event 2026") == "Spring Insight"
    assert pt("Moelis Virtual Discovery Series") == "Events"
    assert pt("London Open House 2026") == "Events"
    assert pt("2027-2028 London Financial Advisory Industrial Placement") == "Industrial Placement"
    assert pt("Off-Cycle Internship – M&A, January 2027") == "Off-Cycle Internship"
    assert pt("Investment Bank Graduate Programme London") == "Graduate Programme"
    assert pt("2027 Summer Analyst, Investment Banking") == "Summer Internship"
    assert len(filters.PROGRAMME_NAMES) == 7


def test_events_and_pre_uni_count_as_early_careers():
    assert filters.is_entry_level("London Open House 2026")
    assert filters.is_entry_level("Sixth Form Work Experience")
    assert filters.is_london("", "2028 Evercore Summer Analyst Coffee Chats - Dartmouth") is False


def test_scope_and_location_extras():
    assert not filters.in_scope("Talent Acquisition Apprenticeship Programme 2027 - London")
    assert not filters.in_scope("Summer 2027 Intern - Disputes, Claims & Investigations")
    assert filters.is_london("", "Summer 2027 Intern: Cleveland, OH") is False
    assert filters.programme_type("FinTech Strategy First Year Analyst") != "Spring Insight"
