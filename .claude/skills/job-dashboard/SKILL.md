---
name: job-dashboard
description: Build or refresh the job-search dashboards from the Notion tracker — a Dashboard section on the Notion "Job Search" page (headline numbers, native Mermaid pie / sankey / weekly bar charts, PNG charts) and an interactive claude.ai artifact dashboard with the same three charts. Use for "dashboard", "charts", "update the dashboard", "可视化", "看板", or the weekly scheduled run.
---

# Dashboards

Both dashboards read only the Notion database. The layout is fixed; a refresh changes data, never design.

## Notion page (every refresh)
`tools/refresh_dashboards.sh` runs:
1. `tools/dashboard_data.py` → `data/dashboard/data.json` (aggregates) and `applications.json` (rows).
2. `tools/charts_png.py` → `pie.png` (stage of every application), `flow.png` (Applied → Confirmed → Interview → Offer with exits),
   `weekly.png` (applications per ISO week by platform).
3. `tools/notion_page.py` → replaces the "Dashboard" section at the top of the Notion page: callout with key numbers,
   link to the interactive dashboard, three Mermaid code blocks (Notion renders `pie`, `sankey-beta`, `xychart-beta` natively)
   and the three PNGs (uploaded through the Notion file-upload API).
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
1. Run `tools/refresh_dashboards.sh` (zsh). On Windows run its four commands one by one instead: `python3 tools/dashboard_data.py`,
   `python3 tools/charts_png.py`, `python3 tools/notion_page.py`, then `python3 tools/backup.py save -m "weekly backup"`.
2. Upload `data/dashboard/applications.json` to `DASHBOARD_URL` as an asset (`asset: true`), then point the `applications`
   dataset at the new file and update its `updated` time (ArtifactData on the dataset document). Do not rewrite the page.
3. Optionally delete the previous asset.

claude.ai pages cannot be embedded in Notion (iframe blocked), which is why Notion gets static charts plus a link.
