---
name: job-scan-apply
description: Daily job scan on LinkedIn, StepStone, Indeed and Xing plus batch applying (platform quick-apply and company career sites with file uploads) — shortlist table with a tailored/template mode per job, user picks, tailored CVs and cover letters where it pays off, prefill to review pages, one confirmation, submit, log to Notion. Use for "scan jobs", "show today's jobs", "apply", "投递", "扫岗位", "看看今天的岗位", "Bewerbungen", or when a scheduled run asks for the scan phase.
---

# Scan and apply

Read `config/profile.yaml`, `knowledge/PROFILE.md` and `knowledge/manifest.yaml` first. Platform details and known traps: `docs/platforms.md`.
When to tailor: `standards/<strategy.country>/apply-strategy.md` (default `de`).
All browsing happens in Claude's **built-in browser pane** (`mcp__Claude_Browser__*`), where the user is logged in.

## The interaction contract (agreed with real users — do not shortcut it)
1. **Scan** → show **one shortlist table** in chat.
2. The user **picks** (e.g. "1,3,5", "all except startups", "全部").
3. You **prefill** every picked job up to its final review page, each in its own tab.
4. You show a **ready list** (what will be sent, which CV, anything unusual).
5. One **confirmation** from the user ("submit" / "提交" / "abschicken") → you submit all and log each.
- If the user already said "submit directly once filled" / "填完直接提交" for this batch, step 4–5 collapse: submit each one as soon as it is filled, and report afterwards. That permission is for the current batch only.
- StepStone **"Ich bin interessiert"** and LinkedIn one-click flows submit instantly. Never click them to "look at the form". They go through steps 1–2 and are sent only after the user picked them.
- A scheduled (unattended) run stops after step 1: it writes the table and logs `Shortlisted` rows. Nothing is ever submitted without the user in the conversation.

## Phase 1 · Scan
1. For each enabled platform, open the searches from `docs/platforms.md#search-urls` for every `search.titles` × `search.locations`
   (posted within `posted_within_days`). Read result lists with `get_page_text`; avoid screenshots.
2. Open each promising posting once and record: title, company, platform, url, city, salary (only if stated), posted,
   `posted` (ISO date if the page shows one, else the platform's text, e.g. "vor 3 Tagen"), `reposted` (true when marked
   "reposted" / "erneut gepostet"), `apply_type` (easy_apply | one_click | platform_form | external), `needs` (cv, cover_letter, degree_certificate, …),
   `size` (large | mid | startup | unknown — check the company page or headcount when unsure), `fit` 0–100, `why` (one line).
3. Save the list to `data/inbox/YYYY-MM-DD.json` and run `python3 tools/dedupe.py data/inbox/YYYY-MM-DD.json`.
   It removes jobs already in Notion, applies the profile filters (blacklist, title filters, startups, cover-letter rule,
   low fit), decides the **Mode** of each job — 🎯 tailored or 📄 template, from posting age, "seen before" and fit, dream
   companies always tailored, at most `strategy.tailored_per_day` tailored — and prints the table. Paste that table to the
   user, at most `max_applications_per_day` rows, with a one-line summary of what was dropped and why, and one line on the
   modes ("🎯 = I write a CV for this posting and ask you a few questions; 📄 = your role-family CV"). The user may switch a
   job's mode when picking ("3 as template").
4. Log every shown job: `python3 tools/log_application.py --status Shortlisted --mode <mode> --posted <date> ...` (so tomorrow's scan skips it).

## Phase 2 · Prepare documents, then prefill (after the user picked)
**🎯 tailored jobs first**: run **job-application-writer** mode J for all of them together — one round of gap questions and
one plus/minus table covering every tailored job, then their CVs (and cover letters where the form has a slot or
`strategy.cover_letter` says so). Prefill the 📄 template jobs while the user answers. The user approves the tailored
documents' text before they are uploaded.

For each picked job, in its own tab:
- **Snapshot the job description first** (postings vanish within weeks; interviews come later): open the posting in the
  built-in browser, `get_page_text`, write that text to a file in your scratchpad, then
  `python3 tools/jd_snapshot.py --url <posting url> --company ... --title ... --platform ... --date <today> --text-file <that file>`
  → `data/applications/<date>_<company>_<title>/` with `jd.md`, `jd.pdf` (readable copy), `page.pdf` / `page.html` (the
  page as loaded). Tailored jobs already have the folder from job-application-writer; the snapshot adds to it. A posting
  that only lives on the company portal (the board links out): snapshot the portal's job page, not the board's teaser.
- **Choose the CV**: 🎯 the tailored PDF from `data/applications/<folder>/`; 📄 the `cv_variants` entry whose `use_for`
  keywords best match the title (default: the first variant). Never edit a template CV for one posting.
- **Materials**: read the form's upload section (slot names, required marks, number of files, size limit), then choose and
  prepare files with the **job-knowledge-base** skill, section C (typed slots → separate unit files; single slot → one merged
  PDF in German standard order; only CV required → CV only; sensitive documents never without asking).
  Form *requires* a cover letter → `rules.cover_letter_required: draft` → job-application-writer "cover letter only"
  (tailored jobs already have one), the user approves the text; `skip` → log `Skipped` with note "requires cover letter".
  Required document not in the knowledge base → pause and ask the user for the file, add it (section A), continue.
- Fill personal data and screening answers from the profile. Never invent answers; if a question is not covered, collect it
  and ask the user once for all jobs together. Add the answer to `screening_answers` so it is never asked again.
- **File uploads** on company sites, by `platforms.upload_method` in the profile (`docs/file-uploads.md`):
  `macos_dialog` → click the page's choose-file control, then immediately run `tools/upload_file.sh "<absolute path>"`;
  `chrome` → do the company-portal application in Claude in Chrome and attach with its `file_upload` tool (file input ref
  from `find` / `read_page`, never click the input); `manual` → click the control, run `tools/copy_path.py "<file>"` and ask
  the user to paste + Enter. Verify the file name appears on the page.
- Stop on the final review page. Do not press the last submit button yet.
- Hand to the user, and continue with the other jobs meanwhile: CAPTCHAs ("what is 4+5"), account registration,
  password fields, e-mail verification links that create an account.

## Phase 3 · Confirm and submit
Show the ready list:

| # | Mode | Company | Title | Platform | Files (slot ← file) | Notes |
|---|---|---|---|---|---|---|

After the confirmation: submit each, wait for the success page or message, then
`python3 tools/log_application.py --status Applied --source auto --platform ... --company ... --title ... --url ...
 --mode tailored|template --cv <CV file name> [--cover-letter] --posted <YYYY-MM-DD> --notes "files: Lebenslauf←…pdf; Zeugnisse←…_Zeugnisse.pdf; jd: data/applications/<folder>/"`
(`--posted` = today minus `age_days` from the shortlist JSON). No snapshot yet (it failed, or the job was submitted in a
hurry) → take it right after submitting; the confirmation page often still links to the posting. Mode and posting date feed the dashboard's
"which applications get interviews" table — the evidence for the strategy.
Report: submitted, skipped (with reason), waiting on the user (CAPTCHA, verification link, missing file).
Respect the daily cap; the user may lift it explicitly for one day.

## After submitting
The next mail sync links each row to its confirmation email (Email Evidence) and moves statuses forward.
When an interview comes in, the saved `jd.pdf` in the application's folder is what to prepare with — the live posting may
be gone. Older applications without a snapshot: `python3 tools/jd_snapshot.py --backfill` (paced; see its docstring).
