# Apply phase (job-scan-apply, after the user picked)

Read this once the user has picked jobs, before touching any form. The interaction contract in `SKILL.md` still applies.
Materials come from `knowledge/manifest.yaml` through the **job-knowledge-base** skill, section C.

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

### SAP SuccessFactors / "j2w" career sites (`jobs.<company>.de`, `/talentcommunity/`, `/default/content/apply/`)
Why this rule exists: on 2026-11-09 two BayernLB roles were logged `Skipped` after ~15 s of blank page; the form was there.
- **Error pattern.** The deep link `…/talentcommunity/apply/<id>` redirects to the home page. The apply page
  (`/default/content/apply/?extJobId=…`) stays blank for 20–60 s and the form sits in a frame page scripts cannot see:
  `document.body.innerText` empty, `find` / `read_page` list only the cookie banner and footer — yet a later screenshot shows the full form.
- **Handling.**
  1. Open the job detail page, decide cookies (*Cookie-Einstellungen ändern* → necessary only → *Meine Auswahl bestätigen*), **really click** *Jetzt bewerben*. Keep the browser pane visible (file dialogs fail while it is hidden).
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

## Phase 2 · Prepare documents, then prefill
1. **Snapshot every picked job's description in one call** (postings vanish within weeks; interviews come later):
   `python3 tools/jd_snapshot.py --from-shortlist data/inbox/YYYY-MM-DD.shortlist.json --rows <picked numbers>`
   → `data/applications/<date>_<company>_<title>/` with `jd.md`, `jd.pdf` (readable copy), `page.pdf` / `page.html`. It fetches
   the postings itself (LinkedIn through its public job card), so their text never passes through the chat. Only for a job it
   reports `blocked`: open the posting in the built-in browser, `get_page_text`, write that text to a scratch file and rerun that
   job with `--url … --company … --title … --platform … --text-file <file> --force`. A posting that only lives on the company
   portal (the board shows a teaser and links out): once you are on the portal's job page, rerun with `--url <portal page> --force`.
2. **🎯 tailored jobs first**: run **job-application-writer** mode J for all of them together — one round of gap questions and
   one plus/minus table covering every tailored job, then their CVs (and cover letters where the form has a slot or
   `strategy.cover_letter` says so). The writer reads the posting from `jd.md`. Prefill the 📄 template jobs while the user
   answers. The user approves the tailored documents' text before they are uploaded.

For each picked job, in its own tab:
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
Then `python3 tools/local_dashboard.py` so the local dashboard shows the new applications.
Report: submitted, skipped (with reason), waiting on the user (CAPTCHA, verification link, missing file).
Respect the daily cap; the user may lift it explicitly for one day.

## After submitting
The next mail sync links each row to its confirmation email (Email Evidence) and moves statuses forward.
When an interview comes in, the saved `jd.pdf` in the application's folder is what to prepare with — the live posting may
be gone. Older applications without a snapshot: `python3 tools/jd_snapshot.py --backfill` (paced; see its docstring).
