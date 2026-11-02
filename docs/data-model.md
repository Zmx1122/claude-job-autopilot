# Data model · 数据结构

## Notion database "Job Applications"
Created by `tools/notion_setup.py`. One row per job (seen, shortlisted, applied or skipped).

| Column | Type | Filled by |
|---|---|---|
| Title | title | scan / mail sync |
| Company | text | scan / mail sync |
| City | text | scan |
| Salary Range | text | scan — only when the posting states it, never guessed |
| First Seen | date | first time the job appeared |
| Applied On | date | submit / first application email |
| Last Email | date | mail sync |
| Platform | select | LinkedIn · StepStone · Indeed · Xing · Other |
| Status | select | see below |
| Source | select | `auto` (Claude applied) · `manual` (found in the inbox, you applied by hand) |
| URL | url | job posting |
| Email Evidence | url | Gmail link to the first submission email |
| Email Thread | url | Gmail thread |
| Job ID | text | reference number from emails |
| Events | text | timeline, e.g. `11-02 application sent via StepStone; 11-03 ats confirmation` |
| Notes | text | interview times, rejection reasons, CV used |

## Status flow · 状态流转
`Seen → Shortlisted → Applied → Confirmed → Interview → Offer`, side exits `Rejected · Withdrawn · Skipped`.
- **Applied** = platform receipt only. **Confirmed** = the company or its ATS acknowledged it.
- The mail sync only moves a status forward (an offer is never overwritten by a later automatic email).

## Local files (`data/`, git-ignored)
| File | What |
|---|---|
| `data/inbox/YYYY-MM-DD.json` | raw scan results; `.shortlist.json` = after dedupe and filters |
| `data/applied.csv` | append-only log of every logged action |
| `data/mail/` | dump, chunks, classifications, `sync_report.md` |
| `data/dashboard/` | aggregates, rows for the artifact, chart PNGs |
