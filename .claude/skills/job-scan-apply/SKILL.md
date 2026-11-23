---
name: job-scan-apply
description: Daily job scan on LinkedIn, StepStone, Indeed and Xing plus batch applying (platform quick-apply and company career sites with file uploads) — shortlist table with a tailored/template mode per job, user picks, tailored CVs and cover letters where it pays off, prefill to review pages, one confirmation, submit, log to Notion. Use for "scan jobs", "show today's jobs", "apply", "投递", "扫岗位", "看看今天的岗位", "Bewerbungen", or when a scheduled run asks for the scan phase.
---

# Scan and apply

**Scan:** read `config/profile.yaml` and the fit-relevant parts of `knowledge/PROFILE.md`
(`sed -n '/^## At a glance/,/^## Documents/p;/^## Coverage/,/^## Ready-made/p' knowledge/PROFILE.md`).
Platform details and known traps: `docs/platforms.md`. When to tailor: `standards/<strategy.country>/apply-strategy.md` (default `de`).
**Apply:** once the user has picked jobs, read [apply.md](apply.md) in this folder before touching any form — best-effort
automation, the never-skip rule, registration walls, Phase 2 (documents, prefill) and Phase 3 (submit, log). A scan-only
(scheduled) run never needs it.
All browsing happens in Claude's **built-in browser pane** (`mcp__Claude_Browser__*`), where the user is logged in.

## The interaction contract (agreed with real users — do not shortcut it)
1. **Scan** → show **one shortlist table** in chat.
2. The user **picks** (e.g. "1,3,5", "all except startups", "全部").
3. You **prefill** every picked job up to its final review page, each in its own tab.
4. You show a **ready list** (what will be sent, which CV, anything unusual).
5. One **confirmation** from the user ("submit" / "提交" / "abschicken") → you submit all and log each.
- If the user already said "submit directly once filled" / "填完直接提交" / "直接投递" for this batch, step 4–5 collapse: apply **Best-effort automation** ([apply.md](apply.md)) — submit each one as soon as it is filled, and report afterwards. That permission is for the current batch only.
- StepStone **"Ich bin interessiert"** and LinkedIn one-click flows submit instantly. Never click them to "look at the form". They go through steps 1–2 and are sent only after the user picked them.
- A scheduled (unattended) run stops after step 1: it writes the table and logs `Shortlisted` rows. Nothing is ever submitted without the user in the conversation.

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
4. Log every shown job in **one** call (so tomorrow's scan skips them):
   `python3 tools/log_application.py --from-shortlist data/inbox/YYYY-MM-DD.shortlist.json --rows <the # numbers you showed, e.g. 1-12> --status Shortlisted`
   Jobs the user does not pick → the same call with `--status Skipped --except-rows <picked numbers> --notes "not picked YYYY-MM-DD"`.
   A single job skipped later (with its reason): `log_application.py --status Skipped --company … --title … --url … --notes "<reason>"`.
   Skipped sets Stage and Applied On to **放弃投递** (never leave Applied On blank once decided).

### Tracker labels
**Applied On** is text (the application date, or `放弃投递`; blank only while the user has not decided). **Stage** (detailed) and
Status (coarse) are set by `log_application.py` from `--status`; `--stage <label>` sets the stage directly (e.g. an interview agreed
by phone: `--stage 一面邀请`; `--stage 接受Offer`). Labels and rules: `tools/stage.py`. The mail sync moves stages afterwards.

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
