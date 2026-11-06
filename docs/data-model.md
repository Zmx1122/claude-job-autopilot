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
| Notes | text | interview times, rejection reasons, files uploaded |
| Mode | select | `tailored` (CV/letter written for this posting) · `template` (role-family CV) — set by the scan |
| CV Version | text | file name of the CV that was sent |
| Cover Letter | checkbox | a cover letter was sent |
| Posted | date | when the posting went online — with Applied On it gives the posting age at application |

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
| `data/dashboard/` | aggregates (incl. interview rate by mode and posting age), rows for the artifact, chart PNGs |
| `data/applications/<date>_<company>_<title>/` | one folder per application: job-description snapshot (`jd.md`, `jd.pdf`, `page.pdf`, `page.html` from `tools/jd_snapshot.py`); for tailored ones also `match.md`, `cv.yaml`, `letter.yaml`, PDFs, `changes.md` |

## Backup folder (`BACKUP_DIR`, default `~/Documents/Job Autopilot Data`)
Mirror of every personal file above (profile, `knowledge/`, `data/applications/`, `data/drafts/`, `applied.csv`) plus a
README, with a hidden git history (one version per `tools/backup.py save`). Not included: `.env`, rebuildable caches,
documents marked `sensitive` (unless `--include-sensitive`).

## Career files (`knowledge/career/`, git-ignored)
| File | What |
|---|---|
| `facts.yaml` | fact bank: entries (work, education, awards …) with achievements, evidence and `confirmed`; skills; languages; open questions. Template: `facts.example.yaml` |
| `interviews/YYYY-MM-DD.md` | the user's answers, verbatim — evidence `interview:YYYY-MM-DD` |
| `DIRECTION.md` | target roles with real postings, gaps, plan (job-career-coach) |
| `cvs/<id>.yaml` | content of master and template CVs; PDFs go to `knowledge/library/cv/` and the manifest |
