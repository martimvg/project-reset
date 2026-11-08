# Applicant Desk prototype

`applicant-desk.html` is the clickable prototype of the website (Tracker, My progress, CV & letters, Interview prep).
It is published as a private page on claude.ai and reads `openings.json` (made by `python -m robot.export_site`, saved in `site/`).

What lives where:
- **Robot code and its results**: this repository (`robot/`, `data/`).
- **Roles checked by hand in Oct–Nov 2026**: `data/hand_checked.json` (copy of the prototype's database).
- **Roles found on job boards for firms that block the robot**: `data/manual.json`.
- **A student's own applications, tasks, CV and interview answers**: stored privately per user inside the claude.ai prototype. They are not in this repository on purpose (this repository is public).

When the real website is built, this file is the design reference: the same sections, rules and wording, rebuilt as a proper web app.
