---
name: job-scan-apply
description: Daily job scan on LinkedIn, StepStone, Indeed and Xing plus batch applying (platform quick-apply and company career sites with file uploads) — shortlist table, user picks, prefill to review pages, one confirmation, submit, log to Notion. Use for "scan jobs", "show today's jobs", "apply", "投递", "扫岗位", "看看今天的岗位", "Bewerbungen", or when a scheduled run asks for the scan phase.
---

# Scan and apply

Read `config/profile.yaml` and `knowledge/manifest.yaml` first. Platform details and known traps: `docs/platforms.md`.
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
   `apply_type` (easy_apply | one_click | platform_form | external), `needs` (cv, cover_letter, degree_certificate, …),
   `size` (large | mid | startup | unknown — check the company page or headcount when unsure), `fit` 0–100, `why` (one line).
3. Save the list to `data/inbox/YYYY-MM-DD.json` and run `python3 tools/dedupe.py data/inbox/YYYY-MM-DD.json`.
   It removes jobs already in Notion, applies the profile filters (blacklist, title filters, startups, cover-letter rule)
   and prints the table. Paste that table to the user, at most `max_applications_per_day` rows, with a one-line summary
   of what was dropped and why.
4. Log every shown job: `python3 tools/log_application.py --status Shortlisted ...` (so tomorrow's scan skips it).

## Phase 2 · Prefill (after the user picked)
For each picked job, in its own tab:
- **Choose the CV** whose `use_for` keywords best match the title; default to the first variant.
- **Materials rule**: upload only what the form requires. CV only when only a CV is required. Form *requires* a cover
  letter → stop, log `Skipped` with note "requires cover letter" (unless `rules.cover_letter_required: generate`).
  Form requires a certificate → use it from the knowledge base; if it is not there, pause and ask the user for the file.
- Fill personal data and screening answers from the profile. Never invent answers; if a question is not covered, collect it
  and ask the user once for all jobs together. Add the answer to `screening_answers` so it is never asked again.
- **File uploads** on company sites: click the page's choose-file control, then immediately run
  `tools/upload_file.sh "<absolute path>"` (see `docs/platforms.md#file-uploads`). Verify the file name appears on the page.
- Stop on the final review page. Do not press the last submit button yet.
- Hand to the user, and continue with the other jobs meanwhile: CAPTCHAs ("what is 4+5"), account registration,
  password fields, e-mail verification links that create an account.

## Phase 3 · Confirm and submit
Show the ready list:

| # | Company | Title | Platform | CV | Notes |
|---|---|---|---|---|---|

After the confirmation: submit each, wait for the success page or message, then
`python3 tools/log_application.py --status Applied --source auto --platform ... --company ... --title ... --url ... --notes "CV-…pdf"`.
Report: submitted, skipped (with reason), waiting on the user (CAPTCHA, verification link, missing file).
Respect the daily cap; the user may lift it explicitly for one day.

## After submitting
The next mail sync links each row to its confirmation email (Email Evidence) and moves statuses forward.
