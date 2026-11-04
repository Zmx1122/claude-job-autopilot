---
name: job-autopilot-setup
description: Guided zero-to-running setup of the job autopilot for a non-technical user — knowledge base (CVs, certificates; no CV → career coaching and a first CV), questionnaire → config/profile.yaml, Notion token + database, Gmail app password + "applications" label, platform logins in Claude's built-in browser, macOS upload permission, dashboards and the daily schedule. Use when the user says "set up", "get started", "配置", "开始", "onboard", when .env or config/profile.yaml is missing, or when tools/check_setup.py fails.
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
- Ask once: "Have you used Job Autopilot before (another computer, or before re-downloading)?" If yes, ask for the backup
  folder (default `~/Documents/Job Autopilot Data`) and run `python3 tools/backup.py restore --from "<folder>"` —
  profile, documents, fact bank and applications come back; continue with the steps `check_setup.py` still shows as open
  (usually only Notion token and Gmail app password, which are never backed up).
- A Chromium browser for writing CV / cover-letter PDFs: `ls "/Applications/Google Chrome.app"` (or Edge / Brave). Missing →
  ask the user to install Google Chrome; only needed for generated documents.
- Tell the user what is coming: about 30–45 minutes once, then a few minutes a day.

## 1. Knowledge base — the user's documents
Ask for every document they might ever need in an application, unsorted is fine: CV variants, degree certificates,
transcripts, Arbeitszeugnisse, language certificates, awards, past cover letters (style samples only), scans and phone photos too.
They drag files into the chat or give paths; copy everything into `knowledge/inbox/`.
Then run the **job-knowledge-base** skill (section A): it splits multi-document PDFs into unit files, names them,
writes `knowledge/manifest.yaml` and `knowledge/PROFILE.md`. Show the user the PROFILE "At a glance" and "Gaps" sections.
Tell them their files stay on this Mac (git-ignored).

### 1b. CVs and the fact bank
- **No CV, or the user is unsure what to apply for** → run the **job-career-coach** skill now: interview, fact bank,
  target roles (`knowledge/career/DIRECTION.md`), then a master CV and one CV per target role family
  (job-application-writer modes M and T). Its search settings feed step 2.
- **CVs exist** → build the fact bank from them (`knowledge/career/facts.yaml`: one entry per position and degree, the CV
  bullets as achievements, `evidence:` the CV's manifest id) and run `python3 tools/facts.py check` and
  `python3 tools/doc_check.py --cv <each CV> --facts knowledge/career/facts.yaml`. Show the user the discrepancies between
  CVs and documents (durations, titles, grades) as open questions — they will matter in every tailored application.
  Offer job-application-writer mode T if a target role family has no fitting CV.

## 2. Questionnaire → config/profile.yaml
Copy `config/profile.example.yaml` to `config/profile.yaml`, then fill it **block by block (Q1–Q8 in the file)**.
- Pre-fill from `knowledge/PROFILE.md` and the manifest facts (degree, grade, languages, employers) before asking anything.
- Pre-fill everything the CV already answers (name, phone, city, degree, years of experience, languages) and show it for a quick OK.
- Ask only what is missing, using AskUserQuestion when there are clear options (remote policy, company size, confirm mode, cover-letter rule).
- Defaults that came out of real use — explain them, let the user change them:
  - `rules.confirm_mode: batch` → you show a shortlist table, the user picks, you prefill all, the user confirms once, you submit.
  - `strategy` block (Q5b): `dream_companies`, fit thresholds, `tailored_per_day: 3` — fresh, high-fit postings and dream
    companies get a tailored CV (and letter); the rest use the template CV of their role family. Explain the decision table in
    `standards/de/apply-strategy.md` in two sentences.
  - `rules.cover_letter_required: draft` → when a form forces a cover letter, Claude drafts one for that posting and the user
    approves it before upload; `skip` skips those jobs instead.
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

## 6. File uploads (one time)
Company portals need real file uploads; the browser pane has no upload tool. Pick the method by system
(`docs/file-uploads.md`) and store it as `platforms.upload_method` in the profile:
- **Windows** → `chrome`: help the user install Google Chrome and the Claude in Chrome extension, connect it, log in to
  the career sites there; test `file_upload` on `tools/upload_test.html`. Fallback `manual` (`tools/copy_path.py`).
- **macOS** → `macos_dialog` (below). Fallback `manual`.
macOS dialog script, see `docs/macos-permissions.md`:
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

## 8b. Backup of personal data
Explain in two sentences: everything personal stays on this computer, outside the shared repo; a copy with version history
goes to a normal folder they can see. Default `~/Documents/Job Autopilot Data` (ask if they prefer another folder; warn
that a folder inside iCloud Drive / OneDrive is uploaded to that cloud). Run `python3 tools/backup.py save -m "setup"`,
then show the folder (reveal it in Finder / Explorer). The weekly dashboard task also saves a backup; Claude saves one after
every change to documents, fact bank or applications. Tokens and passwords are not in the backup — suggest a password manager.

## 9. Final check and hand-over
Run `python3 tools/check_setup.py` until everything required is ✅. Then tell the user, in 5 lines, how a normal day works:
"Each morning I sync your mail and Notion and prepare a shortlist. Open Claude, say 'show today's jobs' / '看看今天的岗位',
pick the ones you like, I fill them in, you confirm once, I submit and log everything."
