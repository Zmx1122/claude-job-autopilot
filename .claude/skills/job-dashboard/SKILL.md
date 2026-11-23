---
name: job-dashboard
description: Build or refresh the job-search dashboards — the local dashboard page (one HTML file opened by double-click, for everyone and the only one for users without Notion: numbers, charts, applications table with emails, JD snapshot and documents per row), and for Notion users a Dashboard section on the Notion "Job Search" page (headline numbers with the total number of applications, PNG charts drawn by the script) and an interactive claude.ai artifact dashboard with the same three charts. Use for "dashboard", "charts", "update the dashboard", "可视化", "看板", or the weekly scheduled run.
---

# Dashboards

All dashboards read only the tracker: the Notion database, or `data/tracker.csv` when `.env` has `TRACKER_BACKEND=local`
(`python3 tools/tracker.py status` says which). The layout is fixed; a refresh changes data, never design.

## Local dashboard (everyone; the only one without Notion)
`python3 tools/local_dashboard.py [--open]` → `data/dashboard/Job-Dashboard.html`, one self-contained file (data inlined, no
internet, no account). Template: `dashboard/local.html` (no data in it; change the design there, never in the generated file).
- Top: tiles (sent, got an interview, waiting for an answer, offers), donut of current status, funnel (sent → receipt confirmed →
  interview → offer, cumulative), applications per week by platform.
- Strategy table "Interview invitation rate vs. posting freshness" (between the weekly chart and the applications table):
  applications grouped by the age of the posting on the day they were sent (same day, 1 day, 2–3 days, 4–7 days, older than
  7 days, posting date unknown) with applications, invitations (reached the interview step at any time, also if rejected later),
  invitation rate as a bar, and how many are still waiting. Groups under 10 applications are marked "small sample"; recent
  applications may still get an answer, so their rate can rise. It is computed in the page from `posted`, `applied` and the
  funnel of each row, so it updates by itself on every rebuild. It is only as good as the `posted` dates: `log_application.py`
  must get `--posted <YYYY-MM-DD>` for every application (job-scan-apply Phase 3 passes today minus `age_days`); rows without it
  land in "Posting date unknown". The Notion page has its own version (block 4 below).
- Table: title, company, status (Stage label + Status), applied date; search and filter chips (all, waiting, interviews, offers,
  rejected / withdrawn, not sent). A click on a row or on ⋯ opens the details: posting link, facts, notes, history (Events),
  the emails of this application (from `data/mail/archive.json`, matched by Gmail thread, else by company + title), the JD
  snapshot text (with a warning when it captured a login wall or bot check) and the files of `data/applications/<folder>/`.
- Rebuilt after every mail sync and every batch of applications (job-mail-sync step 6b, job-scan-apply Phase 3), and by
  `tools/refresh_dashboards.sh`. The user reloads the open page to see the update.
- The user opens it by double-click (or `--open`). To show it in Claude's browser pane, start the `local-dashboard` entry of
  `.claude/launch.json` (serves `data/` on 127.0.0.1:8765) and open `/dashboard/Job-Dashboard.html`; the pane cannot open
  `file://` pages without a permission prompt.
- It holds personal data (emails, notes): it stays in git-ignored `data/dashboard/`; never publish it or send it anywhere (no claude.ai artifact).

With `TRACKER_BACKEND=local` the section below does not apply (no Notion page).

## Notion page (Notion users, every refresh)
`tools/refresh_dashboards.sh` runs:
1. `tools/dashboard_data.py` → `data/dashboard/data.json` (aggregates).
2. `tools/charts_png.py` → `pie.png` (stage of every application), `flow.png` (Applied → Confirmed → Interview → Offer with exits),
   `weekly.png` (applications per ISO week by platform).
3. `tools/notion_page.py` → replaces the "Dashboard" section at the **top** of the Notion page. Fixed layout (user decision 2026-11-10):

   | Order | Block |
   |---|---|
   | 1 | "Dashboard" heading, callout starting with **Total applications: N** (sent; jobs tracked but never applied to counted separately) |
   | 2 | two columns side by side: `pie.png` (stage of every application) · `flow.png` (flow between stages) |
   | 3 | "Applications per week" heading + `weekly.png`, full width, on its own |
   | 4 | "Which applications get interviews" table (lower part, only once rows carry a mode or posting date) |
   | 5 | "Database" heading + the Job Applications database, always at the bottom |

   The section is everything between the "Dashboard" heading and the database; each run replaces it. The API cannot move the
   database, so on an older page (database first) the heading above the database is reused as the "Dashboard" heading. If the
   database is the very first block, the script says so: the user drags the database to the bottom once.
   Only the PNGs (uploaded through the Notion file-upload API); no Mermaid code blocks, Notion shows their source code.
   For wider charts the user turns on ••• → **Full width** for the page once (the API cannot set it).
Needs at least one row; with an empty database it stops with a message.

**There is no claude.ai artifact dashboard** (removed 2026-11-23: it cost many tokens on every refresh for little value). Every refresh is `tools/refresh_dashboards.sh` only: local page + Notion charts. Do not create or update artifacts for the dashboard.
