# Germany · When to tailor (精投) and when a template CV is enough (模版投)

Hiring processes run 2–3 months. A posting that has been open for two months often has finalists already; a late,
carefully tailored application mostly earns a template rejection. Observed in real use: postings applied to within
**3 days** of going online produce most interview invitations; after **7 days** responses are mostly automatic.

## Decision table (used by `tools/dedupe.py`, column "Mode")
| Freshness (posted) | Seen it before? | Fit | Mode |
|---|---|---|---|
| ≤ 24 h | no | ≥ medium | 🎯 tailored |
| ≤ 24 h | yes (familiar) | ≥ medium | 📄 template |
| 1–3 days | no | high | 🎯 tailored |
| 1–3 days | yes | high | 📄 template |
| 1–3 days | any | medium | 📄 template |
| 3–7 days | any | high | 🎯 tailored |
| 3–7 days | any | medium | 📄 template |
| > 7 days | any | any ≥ medium | 📄 template |
| any | any | below medium | not shown (filtered) |

- **Exception**: dream companies and dream roles (`strategy.dream_companies`, `strategy.dream_title_keywords`) are always tailored.
- **Familiar** = the same company posted a similar title before (repost), the platform marks it "reposted / erneut gepostet",
  or the company floods the tracker (≥ 3 postings in 30 days — typical for agencies and some consultancies that post to stay
  visible). The less familiar, the more likely it is a real, fresh opening.
- Fit thresholds: `strategy.fit_high` (default 80), `strategy.fit_medium` (default 60).
- Tailored applications cost the user 10–20 minutes each (questions, review). Cap them with `strategy.tailored_per_day`
  (default 3); the rest fall back to template.

## What the modes mean
- **🎯 tailored**: job-application-writer mode J — match table, gap questions, a CV for this posting, a cover letter when
  the form takes one (or `strategy.cover_letter` says so).
- **📄 template**: one CV per role family (`candidate.cv_variants`), no per-posting edits, cover letter only when the form
  requires one (then a short letter per `rules.cover_letter_required`).
- Template does **not** mean one CV for everything: each role family has its own CV.
- Old postings still deserve a template application — some reopen with a real headcount.

## Search breadth
- LinkedIn has more international, English-friendly companies; StepStone, Indeed and Xing more German Mittelstand.
- Some postings exist only on the company's career site. Large groups (e.g. insurance groups with many subsidiaries) sync
  different subsidiaries to different platforms — scanning one platform shows only part of the market.
