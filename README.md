# Project Reset

A robot that checks company careers sites for entry-level roles in London (spring weeks, summer internships, off-cycle internships, industrial placements and graduate programmes) and keeps a list of the application links.

## How it works

1. **The company list** (`data/companies.csv`): 829 finance employers. The robot only covers the 184 marked IB (investment banking, 138) or PE (private equity, 46) in the `segment` column; the rest are kept for later.
2. **Discovery** (`robot/discover.py`, run monthly or by hand): for each company, finds its careers site and works out which hiring system it uses. Results go to `data/sources.json`, with a plain-English summary in `data/discovery_report.md`.
3. **The check** (`robot/run.py`, every 15 minutes on weekdays, hourly otherwise): reads every known source, keeps entry-level London roles, and updates `data/openings.json`. Roles that disappear are marked closed.
4. **Health** (`data/health.json`): whether each source worked last time. If a source fails three runs in a row, the run is marked as failed and GitHub emails the owner.

## Hiring systems it can read

| System | How it's read |
| --- | --- |
| Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Pinpoint, BambooHR, Personio | Their public job feeds |
| Teamtailor and other sites with an RSS feed | The feed |
| Workday, Oracle Recruiting Cloud, SAP SuccessFactors, Eightfold, Phenom | Searches for entry-level words |
| Avature, iCIMS, Oleeo (tal.net), Jobvite, Radancy | The job list page |
| Taleo and custom-built sites | A screenless Chrome browser that copies the job links |

## Fixing things by hand

- **A company has no source:** add its careers page to `data/seeds.json` (`"company-id": "https://..."`) and run *Discover careers sites* for that company.
- **A source is wrong:** add the correct settings to `data/overrides.json`. Overrides always win.

## Good manners

The robot identifies itself, pauses between requests to the same site, obeys each site's `robots.txt`, and never tries to get past CAPTCHAs or logins.

## Tests

`python -m pytest` checks every reader against sample data. The live check on GitHub confirms the real sites.
