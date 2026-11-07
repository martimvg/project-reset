"""One reader per hiring system. `READERS[name](settings, http)` returns jobs."""
from . import apis, browser, enterprise

READERS = {
    "greenhouse": apis.greenhouse,
    "lever": apis.lever,
    "ashby": apis.ashby,
    "smartrecruiters": apis.smartrecruiters,
    "workable": apis.workable,
    "recruitee": apis.recruitee,
    "pinpoint": apis.pinpoint,
    "bamboohr": apis.bamboohr,
    "personio": apis.personio,
    "rss": apis.rss,
    "workday": enterprise.workday,
    "oracle": enterprise.oracle,
    "successfactors": enterprise.successfactors,
    "eightfold": enterprise.eightfold,
    "phenom": enterprise.phenom,
    "avature": enterprise.avature,
    "icims": enterprise.icims,
    "oleeo": enterprise.oleeo,
    "jobvite": enterprise.jobvite,
    "radancy": enterprise.radancy,
    "browser": browser.browser,  # Taleo, custom sites, anything else
}
