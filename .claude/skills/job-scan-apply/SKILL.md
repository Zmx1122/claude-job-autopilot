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
- If the user already said "submit directly once filled" / "填完直接提交" / "直接投递" for this batch, step 4–5 collapse: apply **Best-effort automation** below — submit each one as soon as it is filled, and report afterwards. That permission is for the current batch only.
- StepStone **"Ich bin interessiert"** and LinkedIn one-click flows submit instantly. Never click them to "look at the form". They go through steps 1–2 and are sent only after the user picked them.
- A scheduled (unattended) run stops after step 1: it writes the table and logs `Shortlisted` rows. Nothing is ever submitted without the user in the conversation.

## Best-effort automation (user rule — always follow)
Once the user has picked jobs and said to apply directly ("直接投递", "全部投", "submit once filled", "尽可能自动化"), the job is to
get every application **all the way to sent**, doing everything a person could do except what a machine must not or cannot do.
- **Do yourself, without asking again:** fill every field from the profile; pick the CV; upload the files the form needs;
  answer Yes/No and screening questions from `screening_answers`; **tick the declaration / consent boxes that the form
  itself requires to submit** ("I confirm I have read the above", data-protection acknowledgement, truthfulness
  certification); click the final submit; read the success message; log `Applied`.
- **Leave to the user, and say exactly which step is open:** CAPTCHAs and "confirm you are human" checks (Cloudflare Turnstile,
  reCAPTCHA challenges, "what is 4+5"); passwords, logins, account creation and verification links that create an account;
  anything that needs a document or fact you do not have; a required cover letter when `rules.cover_letter_required` is `skip`
  (with `draft`, write it and use the user's batch OK).
- **Still not ticked even in auto mode:** optional boxes (newsletter, talent pool, marketing, "keep my data for other jobs").
  Choose the privacy-preserving option.
- **Never stall the whole batch on one blocker.** Open every job in its own tab, prefill all of them, collect the open
  steps, then give the user one list: *job → what is left → which tab*. After the user says it is done, come back, click
  submit and log it. Do not close or navigate away from a tab that waits for the user (form state is lost).
- The daily cap (`max_applications_per_day`) is lifted when the user asks for "all"; say how many you will send.
- **Report faithfully:** `Applied` only after the portal's success page or message. Anything else is *prefilled,
  waiting on you* or *skipped (reason)*. Never claim submitted from a click alone.
- This rule covers the batch the user asked for. It is not a licence to apply to jobs the user did not pick.

## Never skip a job because of a technical problem (user rule — always follow)
`Skipped` is allowed only for a **fact about the job** or a **decision by the user**:

| Valid skip reason | Example |
|---|---|
| Posting closed | "Sorry, this position has been filled", "nicht mehr verfügbar" |
| A filter | blacklist, title filter, posting age, salary, company size, low fit (`dedupe.py`) |
| Already applied | tracker row Applied / Confirmed, StepStone "Schon beworben" |
| Missing material | a required document or fact does not exist; letter required and `cover_letter_required: skip` |
| The user's decision | the user chose to skip, e.g. after a registration recommendation (next section) |

**Never a skip reason:** a blank or slow page, a redirect, a form inside a frame, a blocked popup, an upload or dropdown the tools cannot operate, a human check.
Prefill as far as possible, leave exactly one step open, list the job as *prefilled, waiting on you* with its tab, and let the user decide.
Before writing `Skipped` for anything technical: wait 60 s, look at a screenshot, restart from the job detail page with a real click, tell the user what blocked it.
If it is still impossible keep `Shortlisted`, write the blocker in the note, and ask.

### Why this rule exists: the BayernLB incident (2026-11-09)
Two BayernLB AI roles were logged `Skipped` because `docs/pitfalls.md` said "SuccessFactors portals redirect to the home page: no form, skip".
The user found the roles on LinkedIn and the form was there; both applications were sent later the same day.
- **Root cause 1, wrong entry point.** The deep link `jobs.bayernlb.de/talentcommunity/apply/<id>` redirects to the home page.
  The working path is job detail page → cookie dialog (*Cookie-Einstellungen ändern* → necessary only → *Meine Auswahl bestätigen*) → a **real click** on *Jetzt bewerben*.
- **Root cause 2, judged too early and by the wrong sense.** The apply page (`/default/content/apply/?extJobId=…`) is blank for 20–60 s, and the form sits in a frame
  that page scripts cannot see. It was declared dead after ~15 s from `get_page_text`, never from a screenshot.
- **Error pattern.** Title shows the job, `document.body.innerText` is empty, `find` / `read_page` list only the cookie banner and footer, no inputs in the DOM,
  yet a screenshot taken later shows the full form. Applies to every SAP SuccessFactors / "j2w" career site (`jobs.<company>.de`, `/talentcommunity/`, `/default/content/apply/`).
- **Handling.**
  1. Open the job detail page, decide cookies, **really click** *Jetzt bewerben*. Keep the browser pane visible (file dialogs fail while it is hidden).
  2. Wait up to 60 s and take a **screenshot**; trust it over the DOM.
  3. Drive the form with screenshots, real clicks and real typing (click the field, then type; coordinates are in the screenshot frame; click once per field and check the result).
  4. Uploads: click *…hochladen* → *Vom Gerät* → `tools/upload_file.sh`; confirm the file name on screen.
  5. A required *Motivationsschreiben\** is written with job-application-writer from the fact bank. State experience gaps openly (a posting asking 6–10 years of a candidate with ~2 is not hidden); attach it.
  6. The custom *Anrede* dropdown may not respond to the tools. Fill everything else, ask the user to pick it, and after the user says so **click the final *Meine Bewerbung absenden* yourself**.
     The button stays grey until every required field is set; a grey button is not an error.
  7. Verify the result: a confirmation page, or the portal profile ("Deine Bewerbungen" → *Deine Bewerbung ist bei uns eingegangen*), then log `Applied`.

## Sites that need a registration or login (user rule — never skip these silently)
Examples: Google Careers profile, PwC, BCG talent portal, Instaffo, VKB (temporary login), SAP candidate profiles. Creating the account stays the user's job (CLAUDE.md rule 3),
but **whether it is worth it is your recommendation, not a silent skip** (2026-11-09: five such jobs were logged `Skipped` without a recommendation; the user wanted to be asked).
Put every job that hits a registration wall in one table and recommend:
- **Recommend registering:** fit ≥ `strategy.fit_high` (default 80), a `dream_companies` / `dream_title_keywords` hit, or a role whose hard requirements the profile clearly covers.
- **Recommend skipping:** fit below `strategy.fit_medium` + 10, hard requirements far above the profile (years, a missing mandatory skill), or a portal that asks for much more than the job is worth
  (long assessment, documents we do not have). A stated salary below the user's bar counts too.
- Columns: `# | Company | Title | Fit | Recommendation (register / skip) | One-line reason | Portal`. Then wait for the user.
- After the user registers or logs in (the login persists in the built-in browser), continue with the normal prefill. Log `Skipped` only when the user chose to skip; until then keep
  `Shortlisted` with the note "registration needed – recommendation: register|skip".

## Phase 1 · Scan
**The filters are run-time inputs.** The profile gives the defaults; every run can widen them (`--preset`, `--set`) without
touching `config/profile.yaml` (details in `tools/filters.py`). Start with
`python3 tools/filters.py show [--preset wide] [--set key=value]` — it prints the posting window (and the matching URL parameter
for each platform), the salary rule, the fit threshold, the startup rule and the search titles × locations that apply to this run.
1. For each enabled platform, open the searches from `docs/platforms.md#search-urls` for every `search.titles` × `search.locations`
   (combine titles with OR where the platform allows it), using the window and URL parameters that `filters.py show` printed.
   Read result lists with `get_page_text`; avoid screenshots.
2. Open each promising posting once and record: title, company, platform, url, city, salary (only if stated; set
   `salary_estimated: true` when the platform only estimates it, e.g. StepStone "geschätzt"), `posted`
   (ISO date if the page shows one, else the platform's text, e.g. "vor 3 Tagen"), `reposted` (true when marked
   "reposted" / "erneut gepostet"), `apply_type` (easy_apply | one_click | platform_form | external), `needs` (cv, cover_letter, degree_certificate, …),
   `size` (large | mid | startup | unknown — check the company page or headcount when unsure), `agency` (true when the poster is a
   recruiting agency, headhunter, staffing / Zeitarbeit firm or job aggregator posting for another company; consultancies that hire
   their own staff are employers), `fit` 0–100, `why` (one line).
   **Record every posting you opened. Do not drop anything for salary, age, size or fit yourself** — `dedupe.py` applies the
   filters, so a wider run can be answered from the same file.
3. Save the list to `data/inbox/YYYY-MM-DD.json` and run `python3 tools/dedupe.py data/inbox/YYYY-MM-DD.json [--preset NAME] [--set key=value]`.
   It removes jobs already in Notion, applies the filters (blacklist, title filters, posting age, salary rules, startups,
   cover-letter rule, low fit), decides the **Mode** of each job — 🎯 tailored or 📄 template, from posting age, "seen before" and fit, dream
   companies always tailored, at most `strategy.tailored_per_day` tailored — and prints the table, then **what each filter
   dropped and the exact flag that brings those jobs back**. Paste the table to the user (at most `max_applications_per_day`
   rows unless they ask for more) with the one-line "Dropped by filter" summary, and one line on the
   modes ("🎯 = I write a CV for this posting and ask you a few questions; 📄 = your role-family CV"). The user may switch a
   job's mode when picking ("3 as template").
4. Log every shown job: `python3 tools/log_application.py --status Shortlisted --mode <mode> --posted <date> ...` (so tomorrow's scan skips it).
   Jobs the user does not pick (or skips later) → `--status Skipped`: Stage and Applied On become **放弃投递** (never leave Applied On blank once decided).

### Tracker labels (Notion)
- **Applied On** is text: the application date `YYYY-MM-DD`, or `放弃投递` for jobs never applied to; blank only while the user has not decided (待定).
- **Stage** is the detailed progress, Status the coarse one derived from it (labels and rules: `tools/stage.py`):
  待定 · 放弃投递 · 投递失败 · 已投递 · 已确认收到 · 补交材料 · 测评中 / 测评后被拒 / 测评后撤回 · 简历被拒 · 投递后撤回 ·
  N面邀请 · 已参加N面 · N面邀请后撤回 · N面后撤回 · 参加N面后被拒 (N = 一 二 三 四) · 收到Offer · 接受Offer · 拒绝Offer.
- `log_application.py` sets it from `--status` (Applied → 已投递, Skipped → 放弃投递, Withdrawn → the matching 撤回 label);
  `--stage <label>` sets it directly (e.g. an interview agreed by phone: `--stage 一面邀请`; `--stage 接受Offer`). The mail sync moves it afterwards.

### Widening the search (the user is not happy with the list)
Triggers: "show more", "not enough", "too few", "放宽", "扩大范围", "再多一点", "不要按薪资过滤", "把过去一周也加上".
1. Say in one line what the filters dropped (the "Dropped by filter" line) and offer the matching flag.
2. Re-run **`dedupe.py` on the same raw file** with the wider setting — no new scan needed when the postings are already in the file:
   - `--preset wide` — salary filter off, window 7 days, fit ≥ 60, jobs shortlisted on earlier days show again
   - `--preset everything` — wide, plus window 14 days, fit ≥ 50, startups allowed
   - single changes, e.g. `--set search.salary_filter=off`, `--set search.posted_within_days=10`, `--set strategy.fit_medium=55`,
     `--set search.company_size=any`, `--set search.resurface_shortlisted=true`
3. Only when the new window reaches further back than the scan did (the pages never showed those postings), **re-scan those
   platforms** with the new URL parameters from `python3 tools/filters.py show ...`, append the new postings to the same
   raw file, and re-run `dedupe.py`.
4. The user's own words win: "no salary filter" → `--set search.salary_filter=off`; "include startups" → `--set search.company_size=any`.
   A change is for this run only. Make it permanent only when the user says so ("always", "以后都这样"): edit `config/profile.yaml`,
   or add a named preset under `scan_presets:` for a setting they reuse.
5. Never widened by a preset: the company blacklist, `exclude_titles`, `skip_title_keywords`, jobs already Applied / Rejected /
   Confirmed in the tracker. The daily cap stays unless the user lifts it.

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
