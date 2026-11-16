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
- Table: title, company, status (Stage label + Status), applied date; search and filter chips (all, waiting, interviews, offers,
  rejected / withdrawn, not sent). A click on a row or on ⋯ opens the details: posting link, facts, notes, history (Events),
  the emails of this application (from `data/mail/archive.json`, matched by Gmail thread, else by company + title), the JD
  snapshot text (with a warning when it captured a login wall or bot check) and the files of `data/applications/<folder>/`.
- Rebuilt after every mail sync and every batch of applications (job-mail-sync step 6b, job-scan-apply Phase 3), and by
  `tools/refresh_dashboards.sh`. The user reloads the open page to see the update.
- The user opens it by double-click (or `--open`). To show it in Claude's browser pane, start the `local-dashboard` entry of
  `.claude/launch.json` (serves `data/` on 127.0.0.1:8765) and open `/dashboard/Job-Dashboard.html`; the pane cannot open
  `file://` pages without a permission prompt.
- It holds personal data (emails, notes): it stays in git-ignored `data/dashboard/`; never publish it as an artifact or send it anywhere.

With `TRACKER_BACKEND=local` the sections below do not apply (no Notion page). The claude.ai artifact dashboard can still be
made from `data/dashboard/applications.json` if the user asks for it.

## Notion page (Notion users, every refresh)
`tools/refresh_dashboards.sh` runs:
1. `tools/dashboard_data.py` → `data/dashboard/data.json` (aggregates) and `applications.json` (rows).
2. `tools/charts_png.py` → `pie.png` (stage of every application), `flow.png` (Applied → Confirmed → Interview → Offer with exits),
   `weekly.png` (applications per ISO week by platform).
3. `tools/notion_page.py` → replaces the "Dashboard" section at the **top** of the Notion page. Fixed layout (user decision 2026-11-10):

   | Order | Block |
   |---|---|
   | 1 | "Dashboard" heading, callout starting with **Total applications: N** (sent; jobs tracked but never applied to counted separately), link to the interactive dashboard |
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

## Interactive dashboard (claude.ai artifact)
**First time** (no `DASHBOARD_URL` in `.env`):
1. Artifact tool `action: "quickstart"`, `intent: "other"` — use the **Dashboard** type it offers.
2. Create it from that type with the title "Job Search Dashboard". Follow the instructions the type returns; they are authoritative.
   The usual shape: attach `data/dashboard/applications.json` as the dataset named **applications**, and use
   `dashboard/index.html` from this repo as the page (it already defines the calcs `status_counts`, `kpis`, `flow`, `weekly`,
   `by_platform`, `open_pipeline` and draws the donut, the Sankey, the weekly bars and the open-pipeline table).
3. Save the artifact link to `.env` as `DASHBOARD_URL` and re-run `tools/notion_page.py` so the Notion page links to it.

**Refresh** (weekly, or after a big sync):
1. Run `tools/refresh_dashboards.sh` (zsh). On Windows run its commands one by one instead: `python3 tools/dashboard_data.py`,
   `python3 tools/local_dashboard.py`, `python3 tools/charts_png.py`, `python3 tools/notion_page.py`, then `python3 tools/backup.py save -m "weekly backup"`.
2. Upload `data/dashboard/applications.json` to `DASHBOARD_URL` as an asset (`asset: true`), then point the `applications`
   dataset at the new file and update its `updated` time (ArtifactData on the dataset document). Do not rewrite the page.
3. Optionally delete the previous asset.

claude.ai pages cannot be embedded in Notion (iframe blocked), which is why Notion gets static charts plus a link.
