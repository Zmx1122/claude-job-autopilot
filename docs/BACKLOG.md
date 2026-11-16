# Backlog — what to build next

Ideas and known gaps, newest first. Each item: the problem as seen in a real run, then the direction.
When an item is done, delete it here and mention it in the PR.

## From the 2026-11-13 batch run (33 picks → 13 sent)

### 1. Human checks (reCAPTCHA, Cloudflare Turnstile) block the last click
- **Seen:** Indeed quick-apply ends in a reCAPTCHA; every Personio form (Mawave, iits, KI•PIE) has a Cloudflare
  Turnstile that does not pass in the built-in browser at all, even for the user. 3 fully prefilled jobs had to be skipped.
- **Not planned:** solving or bypassing the checks automatically. That defeats the site's bot protection, breaks the
  portals' terms, and Claude will not do it (CLAUDE.md rule 3).
- **Direction (allowed):**
  - Detect the check at scan time (Personio, Indeed quick-apply, Dover) and show it in the shortlist ("human check at the end"),
    so the user decides before the work is done.
  - One "hand-off queue": bring each waiting tab to the front in turn and wait for the user's tick, instead of a list of tabs.
  - Personio Turnstile fails in the built-in browser: try the same form in Claude in Chrome (the user's real browser),
    where the user can pass it; or offer the company's e-mail application address when the posting gives one.
  - Send a push notification when a tab waits on a human check, so the user can tick it while the batch goes on.
- **Fewer checks in the first place (2026-11-16 review):** challenges come from anonymous, fast or headless traffic, not from
  a signed-in user reading at human speed. So:
  - **Scan from sources that have no challenge page.** (a) The job-alert emails LinkedIn, StepStone, Indeed and Xing already
    send: the mail sync classifies them as `job_alert` and ignores them; parse their job links into the scan input instead of
    opening search pages. (b) Official feeds: the Bundesagentur für Arbeit job search API (public, documented on bund.dev),
    and the public job JSON of the ATS systems many target companies use (Greenhouse, Lever, Ashby, Personio XML,
    SmartRecruiters) for a watch list of companies. Check each source's terms before building it.
  - **Never fetch Indeed / LinkedIn anonymously.** 5 JD snapshots (4 Indeed, 1 LinkedIn) were Cloudflare pages saved as the
    posting (fixed: `jd_snapshot.py` now marks them blocked). Take snapshots only from the signed-in browser pane (`--text-file`);
    redo the blocked ones with `jd_snapshot.py --backfill --redo` from the pane.
  - **Pace the browser:** one tab at a time per platform during a scan, a few seconds between page loads, no burst of 20 tabs.

### 2. Account registration and e-mail verification codes
- **Seen:** NTT DATA (SuccessFactors register), Dräger (portal login), Wolters Kluwer (new Workday tenant), AWS (amazon.jobs),
  HDI (existing account), Avanade/Accenture and Deutsche Bank (Workday login). About a third of the picks.
- **Not planned:** creating accounts, choosing passwords, or reading verification codes from Gmail and typing them.
  Account creation and codes stay with the user or their password manager (CLAUDE.md rule 3; Claude's safety rules).
- **Direction (allowed):**
  - A registration table already exists (job-scan-apply). Add: prefill the registration form up to the password field and
    hand that tab to the user; after the user's login, continue the application automatically.
  - Password-manager hand-off where the client supports it (the user approves each fill in the manager; Claude never sees it).
  - Remember per tenant that an account exists (`config/portal_accounts.yaml`, no secrets) so the scan can show
    "login needed (account exists)" vs "registration needed".
  - Workday: one login per tenant covers all jobs of that tenant (Avanade + Accenture share `accenture.wd103`) — group them.

### 3. Stored CVs on job platforms go stale
- **Seen:** Indeed and StepStone still held July/early-November CVs ("PhD candidate", "Lecturer") and would have sent them.
- **Direction:** before a batch, check the CV stored on Indeed, StepStone and LinkedIn against `knowledge/library/cv/`
  and list the outdated ones; replacing or deleting a stored CV is an account change → ask the user once per platform.

### 4. StepStone "Ich bin interessiert" is often only a link-out
- **Seen:** HDI, KVB: the button opens the company site (blocked new tab) and StepStone shows "Hat mit deiner Bewerbung alles geklappt?".
  Nothing was sent.
- **Direction:** at scan time record the real apply target (company portal URL) for every StepStone job, so apply never
  relies on the button; treat that confirmation page as "not applied" in code, not only in docs.

### 5. Daily prune vs. jobs waiting on the user
- **Seen:** `tools/prune_shortlisted.py` deletes rows still Shortlisted after 2 days. Jobs that wait on a login or an answer
  are also Shortlisted and would disappear.
- **Decide with the user:** a separate status (e.g. `Waiting`) that the prune skips, or keep deleting them.

### 6. Smaller ones
- Hidden browser pane = no file dialog: warn once at batch start and pause instead of failing per job.
- Porsche portal (`jobs.porsche.com`) returned HTTP 500 for every job page on 2026-11-13 — add a retry-later queue.
- Tailored-mode questions (gap questions, essays, "why us") are asked one job at a time; collect them for the whole batch
  into one message before any prefill starts.
