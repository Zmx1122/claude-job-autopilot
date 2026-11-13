# Platform playbook

How each platform behaves when Claude applies through the built-in browser pane, learned from real applications
(German UIs, late 2026). Update this file whenever a platform changes.

## Search URLs
Starting points; replace `{q}` with a URL-encoded title and `{loc}` with a city. Check the filters on the page after loading.

| Platform | URL | Notes |
|---|---|---|
| LinkedIn | `https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}&f_TPR=r86400` | `f_TPR=r86400` = last 24 h (`r172800` = 48 h). Add `&f_AL=true` for Easy Apply only. |
| StepStone | `https://www.stepstone.de/jobs/{q-with-dashes}/in-{loc}?radius=30&ag=age_1` | `ag=age_1` = last 24 h. Results mix one-click, on-site forms and external links. |
| Indeed | `https://de.indeed.com/jobs?q={q}&l={loc}&fromage=1` | `fromage` = days. "Schnellbewerbung" / "Einfach bewerben" = quick apply. |
| Xing | `https://www.xing.com/jobs/search?keywords={q}&location={loc}&sort=date` | Mostly redirects to company portals. |

## LinkedIn (Easy Apply)
- Steps: contact (prefilled) → resume (choose from the LinkedIn library only) → questions → review.
- Easy Apply upload works: click "Lebenslauf hochladen" by ref, then `tools/upload_file.sh`; the new file is selected and stays in the library. (Earlier note said the pane cannot upload — it can, with the macOS dialog script.)
- German UI: the review step opens with **"Überprüfen"**/"Feedback geben"; the final button is **"Bewerbung senden"** — only that one needs the user's OK.
- Untick "Unternehmen folgen". After sending, the #OpenToWork prompt → "Nein, danke".
- Non-Easy-Apply jobs open the company site → see Company portals.

## StepStone — three different flows
1. **One-click** ("Ich bin interessiert" on Schnelle-Bewerbung jobs): sends immediately with the CV and data stored in the account.
   There is no review page. Only click after the user picked the job.
2. **On-site smart-apply form**: React dropdowns ignore values set by script (`form_input`), so the submit button stays grey.
   Open the dropdown with a real click, then choose with the keyboard (type, Arrow, Enter).
3. **External**: link to the company portal → Company portals.
- Forms that make "Anschreiben" mandatory → skip (default rule).

## Indeed
- Schnellbewerbung requires a login; check for a logged-in header before starting, the quick-apply page can look normal without one.
- Indeed reuses the first file ever uploaded. If that is a merged multi-page PDF, choose **"Andere Datei hochladen"** and upload the single CV
  (the page's file dialog works with `tools/upload_file.sh`).
- Final step: "Bewerbung einreichen".

## Xing
- Most postings redirect to the company portal; the Xing job page itself rarely has a form.
- Answer "Wie sind Sie auf uns aufmerksam geworden?" with XING when that is where the job was found.

## Company portals and ATS
| Portal | What to expect |
|---|---|
| SmartRecruiters | Form inside shadow DOM; no accessibility refs. Upload via the OS dialog (`upload_file.sh`). Confirmation mail "We received your application". |
| Porsche (jobs.porsche.com) | No login. Privacy page has a math CAPTCHA → the user answers it. 3 pages: personal data → salary + source → attachments (CV + "Zeugnis höchster Bildungsabschluss" required). Choose the attachment **type first**, then the file. The upload button is a hidden `label[for=btn-attachment]` (scroll to top, it sits at the top-left). The upload does not start by itself: trigger `#start_file_upload_button`. After an upload the page can re-render without its dropdown widget → reload the page (the uploaded files stay). After submitting, an email verification link also **creates a portal account** → the user clicks it. |
| Oracle Recruiting | Wants a single PDF combining CV, references and degree certificates → `tools/kb_bundle.py --merge` in German standard order (job-knowledge-base skill, section C). |
| Greenhouse | Use the embed form `boards.greenhouse.io/embed/job_app?for=<board>&token=<gh_jid>` (no cookie wall). Text fields accept the native value setter + input event; react-select dropdowns: click, type, Enter. File upload: click the **`label` "Attach" by its ref** (coordinate clicks on the button opened nothing) and then run `upload_file.sh`. Export-control checkboxes: click by ref. |
| Ashby (e.g. OpenAI) | Single page, no account. Click fields and type; location is an autocomplete (choose the option); date as MM/DD/YYYY; Yes/No are buttons; reCAPTCHA is invisible. |
| Google Careers | Requires creating a Google Careers profile before the first application → the user does that. |
| Personio, softgarden, Workday, SuccessFactors | Usually standard file inputs; some require an account (user creates it). SuccessFactors / j2w sites (e.g. BayernLB) load slowly and hide the form in a frame: see the skill section "Never skip a job because of a technical problem". Personio and Dover show a Cloudflare check that fails in the built-in browser. |

## File uploads
Three methods — macOS dialog script, Claude in Chrome (Windows), manual paste — see **`docs/file-uploads.md`**. With the macOS script:
1. Click the page's choose-file control in the browser pane (a real click; a script `.click()` often opens nothing).
2. Within ~10 s run `tools/upload_file.sh "/absolute/path/file.pdf"`.
3. Verify the file name appears on the page. If the portal needs a category per file, set it before step 1.
Requires macOS Accessibility for Claude, see `docs/macos-permissions.md`.

## General
- Screenshot coordinates on a Retina Mac are CSS pixels × 2.
- If the browser pane is closed mid-form, the form state is lost; reopen and re-check consent boxes.
- Address, salary, notice period, start date and work permit appear on most German portals; keep them in the profile.

## Portal notes added 2026-11-10
- **Deloitte (de-job.deloitte.com, Eightfold)**: no account needed; the CV from an earlier application stays attached. Gender is required on submit.
  Deloitte limits applications per candidate: the submit API answers HTTP 429 "Maximale Anzahl an Bewerbungen erreicht" (seen one day after
  another Deloitte application). The page shows no message — read the network response. Valid skip reason (limit reached).
- **Ashby AI-evaluation consent** ("By selecting Yes, I am consenting to the use of AI for evaluating my candidacy"): answer from
  `screening_answers.ai_evaluation_consent`. Ashby Yes/No buttons: use real clicks; a JS `click()` can land on the wrong question.
- **GetYourGuide**: Ashby board slug is `getyourguide.careers` (jobs.ashbyhq.com/getyourguide.careers/<jid>/application).
- **HDI (job.hdi.group)**: use the hidden "QuickApply" link (hdi-production.p78quickapply.com …?Reqid=<id>) — no account; CV upload →
  tag it "Lebenslauf" → data page (UI5 selects: open, then type a letter / arrows + Enter). Anrede is required although unmarked until submit.
- **adesso (jobs.adesso-group.com, SuccessFactors j2w)**: BayernLB pattern — form not in the DOM, drive by screenshots. One upload slot
  "CV / komplette Unterlagen" → merged PDF (kb_bundle --merge). Street/PLZ/date fields may not accept typing (optional).
- **valantic**: modal form with native inputs (native value setter works); salary is a range slider (set value + input event).
- **SmartRecruiters (ServiceNow)**: CV parse can split one job into two experience entries with a wrong title — delete the bad one.
- **Personio (SQUER)**: "Add file" works only when the click and `upload_file.sh` run one after the other (not in parallel).

## Scan notes added 2026-11-13
- **Xing date filter has a URL parameter after all:** `&sincePeriod=LAST_24_HOURS` (the sidebar "in den letzten 24 Stunden" sets it). The search URL also
  redirects to `/jobs/search/ki?...`. Salary ranges on Xing cards are Xing's own estimates ("von XING geschätzt") unless the ad text states one.
- **StepStone result pages append CV-based suggestions** ("Vorschläge basierend auf deinem Lebenslauf", many older than the `ag=` window) after the
  real hits. Read the posting date on each card ("vor N Stunden/Tagen") and ignore anything older than the window.
- **StepStone one-click detail pages** show only "Ich bin interessiert" in `get_page_text`; the description is in a `<section>` — read it with
  `javascript_tool` (`section` elements with long `innerText`). Never click the button to see more.
- **Indeed:** OR-queries and `sort=date` return mostly unrelated jobs; a plain keyword (`q=%22AI+Engineer%22` or `q=LLM+Agent`) with relevance sort
  and `fromage=3` works better. Cards marked "Anzeige" are ads outside the window.
