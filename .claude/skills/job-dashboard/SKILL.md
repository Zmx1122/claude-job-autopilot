---
name: job-dashboard
description: Build the job-search dashboards from the Notion tracker — native Notion charts on the "Job Search" page (total applications, status donut, stage bars, applications per week, interviews by CV mode; live, no script) created through Claude's Notion connector, and an optional interactive claude.ai artifact dashboard. Use for "dashboard", "charts", "update the dashboard", "可视化", "看板", or the weekly scheduled run.
---

# Dashboards

The Notion dashboard is made of **native Notion chart views** of the Job Applications database. They update live with
every row change, so there is nothing to refresh. Claude creates them once through the **Notion connector** (Claude desktop
→ Settings → Connectors → Notion), which must be signed in to the same workspace as the integration token in `.env`.

## Requirement: the Notion connector
1. `notion-get-self` (Notion connector) → workspace name.
2. The tracker's workspace: `GET https://api.notion.com/v1/users/me` with `NOTION_TOKEN` → `bot.workspace_name`.
3. They must match. If not (or the connector is missing): the user opens Claude desktop → Settings → Connectors → Notion →
   Connect (or Disconnect → Connect) and picks that workspace, giving access to the "Job Search" page. Then check again.
Without the connector there is no Notion dashboard; the tracker itself (scripts with `NOTION_TOKEN`) works anyway.

## Notion page (once; again only if the layout was broken)
Columns the charts use (created by `tools/notion_setup.py`): **Applied Date** (date, written by every tool next to the text
column Applied On), **Applied Week** (formula `formatDate(prop("Applied Date"), "GGGG-[W]WW")`), Status, Stage, Platform, Mode.
`notion-fetch` the database for its `collection://` data source, then create five chart views with `notion-create-view`
(`parent_page_id` = the Job Search page, `type: chart`, `show_data_source_title: false`):

| Name | `configure` |
|---|---|
| Total applications | `FILTER "Applied Date" IS NOT EMPTY; CHART number AGGREGATE count CAPTION "Applications sent (…)"` |
| Where every application stands | `FILTER "Applied Date" IS NOT EMPTY; GROUP BY "Status"; CHART donut COLOR colorful HEIGHT large` |
| How far applications got | `FILTER "Applied Date" IS NOT EMPTY; GROUP BY "Stage"; CHART bar COLOR colorful HEIGHT large SORT y_descending` |
| Applications per week | `FILTER "Applied Date" IS NOT EMPTY; GROUP BY "Applied Week"; CHART column STACK BY "Platform" COLOR colorful HEIGHT medium SORT x_ascending` |
| Which applications get interviews | `FILTER "Applied Date" IS NOT EMPTY; FILTER "Mode" IS NOT EMPTY; GROUP BY "Mode"; CHART bar STACK BY "Status" COLOR colorful HEIGHT small` |

New views land at the end of the page. `notion-fetch` the page, then `notion-update-page` → `replace_content` with this
layout (copy every `<database url=… data-source-url=…>` tag exactly; the main database keeps its tag and title):

```
# Dashboard
<database …Total applications…></database>
<columns>
<column><database …Where every application stands…></database></column>
<column><database …How far applications got…></database></column>
</columns>
## Applications per week
<database …Applications per week…></database>
## Which applications get interviews
<database …Which applications get interviews…></database>
# Database
<database …Job Applications (main)…>Job Applications</database>
```
Then `notion-update-page` → `update_properties` with `full_width: true`. Fetch the page once more and check the order.
Notes: a chart cannot group a date by week (the DSL has no such modifier), hence the Applied Week formula. Notion's free
plan allows one chart; the full dashboard needs a paid plan, on free keep only "Total applications" or "Where every
application stands" (user's choice). Layout decided by the user on 2026-11-10: charts on top, two side by side, weekly on
its own, interview chart below, database at the bottom.

## Interactive dashboard (claude.ai artifact, optional)
**First time** (no `DASHBOARD_URL` in `.env`):
1. Artifact tool `action: "quickstart"`, `intent: "other"` — use the **Dashboard** type it offers.
2. Create it from that type with the title "Job Search Dashboard". Follow the instructions the type returns; they are authoritative.
   The usual shape: attach `data/dashboard/applications.json` as the dataset named **applications**, and use
   `dashboard/index.html` from this repo as the page (it already defines the calcs `status_counts`, `kpis`, `flow`, `weekly`,
   `by_platform`, `open_pipeline` and draws the donut, the Sankey, the weekly bars and the open-pipeline table).
3. Save the artifact link to `.env` as `DASHBOARD_URL`.

**Refresh** (weekly, or after a big sync):
1. `python3 tools/dashboard_data.py` → `data/dashboard/applications.json`, then `python3 tools/backup.py save -m "weekly backup"`.
2. Upload `data/dashboard/applications.json` to `DASHBOARD_URL` as an asset (`asset: true`), then point the `applications`
   dataset at the new file and update its `updated` time (ArtifactData on the dataset document). Do not rewrite the page.
3. Optionally delete the previous asset.

claude.ai pages cannot be embedded in Notion (iframe blocked); the Notion page uses its own native charts instead.
