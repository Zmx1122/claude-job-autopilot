---
name: job-autopilot-setup
description: Guided zero-to-running setup of the job autopilot for a non-technical user — knowledge base (CVs, certificates), questionnaire → config/profile.yaml, Notion token + database, Gmail app password + "applications" label, platform logins in Claude's built-in browser, macOS upload permission, dashboards and the daily schedule. Use when the user says "set up", "get started", "配置", "开始", "onboard", when .env or config/profile.yaml is missing, or when tools/check_setup.py fails.
---

# Job Autopilot setup

You are onboarding someone who may never have used a terminal. You run every command yourself; the user only
clicks in Notion, Gmail, System Settings and the browser pane, and answers questions. Speak the user's language
(Chinese, German or English, whatever they write in). Keep each message short: one step, what to click, what to send back.

Track progress with the task list. Steps 1–9 below. Skip a step that `python3 tools/check_setup.py` already shows as done.
Never paste secrets back into chat, never type a password or solve a CAPTCHA, never create accounts for the user.

## 0. Prepare (you, 1 minute)
- `python3 --version` (needs 3.9+). If missing on macOS: ask the user to run `xcode-select --install` or install from python.org.
- `python3 -m pip install -r requirements.txt`
- `cp -n .env.example .env`
- Tell the user what is coming: about 30–45 minutes once, then a few minutes a day.

## 1. Knowledge base — the user's documents
Ask for every document they might need in an application: CV variants (PDF), degree certificate, work references
(Arbeitszeugnisse), language certificates, past cover letters (as style samples only).
- They can drag files into the chat or give paths. Copy each file into the right folder:
  `knowledge/cv/`, `knowledge/certificates/`, `knowledge/cover_letters/`, `knowledge/other/`. Use clear names
  (`CV-AI-Engineer.pdf`, `Master-Degree.pdf`). Keep originals untouched.
- Read every PDF (pdf skill or `pypdf`). Split merged PDFs into one file per purpose: portals reject a 10-page "everything" PDF
  as a CV, and Indeed stores whatever you upload first.
- Write `knowledge/manifest.yaml`: for each file `path`, `kind` (cv | degree_certificate | work_reference | language_certificate | cover_letter_sample | other),
  `language`, `pages`, `summary` (one line), `use_for` (job-title keywords, CVs only).
- The folder contents are git-ignored; tell the user their files stay on this Mac.

## 2. Questionnaire → config/profile.yaml
Copy `config/profile.example.yaml` to `config/profile.yaml`, then fill it **block by block (Q1–Q8 in the file)**.
- Pre-fill everything the CV already answers (name, phone, city, degree, years of experience, languages) and show it for a quick OK.
- Ask only what is missing, using AskUserQuestion when there are clear options (remote policy, company size, confirm mode, cover-letter rule).
- Defaults that came out of real use — explain them, let the user change them:
  - `rules.confirm_mode: batch` → you show a shortlist table, the user picks, you prefill all, the user confirms once, you submit.
  - `rules.cover_letter_required: skip` → jobs that force a cover letter are skipped (no generic letters).
  - `rules.certificate_required: ask` → if a form demands a certificate that is not in the knowledge base, pause and ask.
  - `search.company_size: established` and `skip_title_keywords: [Founding]` if the user wants mature employers only.
  - `search.max_applications_per_day: 10`.
- Address, salary, notice period, start date and work permit are asked by most German portals — make sure they are filled.

## 3. Notion (tracker + dashboard page)
Walk the user through `docs/credentials.md#notion` one click at a time:
1. notion.so/profile/integrations → **New integration** → type Internal → name `Job Autopilot` → copy the **Internal Integration Secret** (`ntn_…`).
2. Create a page "Job Search" in their workspace (top level). Page → `•••` → **Connections** → add `Job Autopilot`.
3. Copy the page link.
Ask them to paste the secret into `.env` themselves (open it with the open_in_editor tool if available, else `open -e .env`).
If they prefer to paste it into chat, accept it, write it to `.env`, and do not repeat it back.
Then run `python3 tools/notion_setup.py` — it creates the **Job Applications** database (15 columns) and stores its id.

## 4. Gmail (status tracking + the "applications" label)
`docs/credentials.md#gmail`:
1. Use the inbox they apply with (ideally the same address as `candidate.email`).
2. Turn on 2-Step Verification → myaccount.google.com/apppasswords → create `job-autopilot` → 16-letter password into `.env`
   as `IMAP_APP_PASSWORD`, address as `IMAP_USER`.
3. `python3 tools/gmail_setup.py`.
   - Label exists → done.
   - Missing → ask: "Create a Gmail label `applications` for all application emails?" On yes: `python3 tools/gmail_setup.py --create`.
     If the script lists related labels the user already uses (e.g. `Bewerbungen`), offer to reuse one by setting `GMAIL_LABEL` in `.env`.
4. Optional backfill: if they applied before, ask from which date; run the **job-mail-sync** skill in backfill mode.

## 5. Platform logins in Claude's built-in browser
Use the built-in browser pane (`mcp__Claude_Browser__*`), not Chrome. Logins persist in the pane.
For each enabled platform open the login page with `preview_start {url}` and ask the user to sign in themselves
(tick "keep me signed in"). Then verify by loading a page that needs login.
- LinkedIn `https://www.linkedin.com/login` — afterwards upload every CV variant once to the resume library
  (Settings → Data privacy → Job application settings), because Easy Apply can only pick from that library.
- StepStone `https://www.stepstone.de/` → Anmelden. Upload the default CV to the profile.
- Indeed `https://secure.indeed.com/account/login` — Schnellbewerbung needs a login. Replace any stored multi-page PDF with the single CV.
- Xing `https://login.xing.com/`.
Company career portals (Porsche, SAP, Siemens …) are handled per application; some need an account — the user creates those.

## 6. File-upload permission (macOS, one time)
Company portals need real file uploads; the browser pane has no upload tool, so `tools/upload_file.sh` drives the macOS
Open dialog. See `docs/macos-permissions.md`.
1. Ask the user: System Settings → Privacy & Security → **Accessibility** → turn on **Claude** (add it with + if missing).
2. Test: open `tools/upload_test.html` in the pane (`preview_start file://<abs path>`), click the file input, run
   `tools/upload_file.sh <abs path of a CV>`, check the page shows the file name.
3. If it fails with "not allowed assistive access": the toggle is off or Claude was updated — toggle off/on.
   Never build a helper .app with osacompile as a workaround: each rebuild is a new identity and loses the permission.

## 7. Dashboards
- Notion: after the first rows exist, run the **job-dashboard** skill (adds charts to the "Job Search" page).
- Interactive: the same skill creates a claude.ai artifact dashboard and stores its link as `DASHBOARD_URL`.

## 8. Schedule (Claude desktop scheduled tasks)
Create two scheduled tasks with the scheduled-tasks tool (ask the user for times; defaults from `schedule:` in the profile):
- **job-autopilot-daily** (e.g. weekdays 08:00): prompt =
  "In the job-autopilot repo: run the job-mail-sync skill (daily mode, apply after reviewing the report), then the
  scan phase of the job-scan-apply skill, and leave the shortlist table for me. Do not submit any application."
- **job-autopilot-weekly-dashboard** (e.g. Monday 08:00): prompt = "In the job-autopilot repo: run the job-dashboard skill (refresh)."
Explain: tasks run only while the Mac is awake and the Claude app is open. Submitting always happens in a session with the user.

## 9. Final check and hand-over
Run `python3 tools/check_setup.py` until everything required is ✅. Then tell the user, in 5 lines, how a normal day works:
"Each morning I sync your mail and Notion and prepare a shortlist. Open Claude, say 'show today's jobs' / '看看今天的岗位',
pick the ones you like, I fill them in, you confirm once, I submit and log everything."
