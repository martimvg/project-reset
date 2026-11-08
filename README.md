# Project Reset

A robot that checks company careers sites for entry-level investment banking and private equity roles in London and keeps a list of the application links, sorted into seven types: Summer Internship, Graduate Programme, Off-Cycle Internship, Industrial Placement, Spring Insight, Pre-Uni and Events.

## How it works

1. **The company list** (`data/companies.csv`): 829 finance employers. The robot only covers the 184 marked IB (investment banking, 138) or PE (private equity, 46) in the `segment` column; the rest are kept for later.
2. **Discovery** (`robot/discover.py`, run monthly or by hand): for each company, finds its careers site and works out which hiring system it uses. Results go to `data/sources.json`, with a plain-English summary in `data/discovery_report.md`.
3. **The check** (`robot/run.py`, every 15 minutes on weekdays, hourly otherwise): reads every known source, keeps entry-level London roles, and updates `data/openings.json`. Roles that disappear are marked closed.
4. **Health** (`data/health.json`): whether each source worked last time. If a source fails three runs in a row, the run is marked as failed and GitHub emails the owner.

## The rules, in plain words

Every job the robot reads goes through four questions. It is kept only if the answers are yes, yes, yes.

1. **Is it for students or new graduates?** The title must contain a student word (intern, internship, summer analyst, graduate, spring week, insight, off-cycle, placement, work experience, apprenticeship, sixth form, open house, a year 2026–2029 next to "analyst", and similar). It is thrown out if it contains a senior word (vice president, director, manager, senior, MBA, summer associate…).
2. **Is it investment banking or private equity work?** Thrown out if the title names another part of the bank: technology, operations, sales, trading, research, wealth or asset management, audit, tax, risk, compliance, HR, marketing, insurance and similar.
3. **Is it in London?** Kept if London or Canary Wharf is named. Thrown out if another city (New York, Paris, Manchester…) or "US" is named. Kept but flagged "Not stated" if the site gives no location.
4. **Which type is it?** The first match wins, in this order: Pre-Uni (sixth form, year 12, school leaver, apprenticeship) → Spring Insight (spring week, insight day/week, discovery day, first-year) → Events (open house, coffee chat, webinar, discovery series) → Industrial Placement (placement, placement year) → Off-Cycle Internship (off-cycle, 6-month internship, January start) → Graduate Programme (graduate, full-time analyst, entry level) → Summer Internship (summer, intern).

Extra rules for pages read with the browser (sites without a job feed): menu links such as "Graduates" or "FAQs" are ignored. A link counts only if it names something specific, such as a year, "analyst" or a deal team (M&A, corporate finance…).

**History:** a role that disappears from a working site is marked *Closed* with the date, and stays in the list.

**Roles added by hand** (for example ones you apply to by email) live in `data/manual.json`, or are added with the *Add a role* button on the website.

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

## Finding the right job board for a firm

Run *Probe careers pages* from the Actions tab. It opens each careers page in a screenless browser and lists the job systems the page uses (see the `probe-results` files on the run).

## Good manners

The robot identifies itself, pauses between requests to the same site, obeys each site's `robots.txt`, and never tries to get past CAPTCHAs or logins.

## Tests

`python -m pytest` checks every reader against sample data. The live check on GitHub confirms the real sites.
