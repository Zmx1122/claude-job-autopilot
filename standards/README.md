# Country standards · 各国求职标准

Rules that change from country to country live here, one folder per country (ISO code). The skills read the folder named by
`strategy.country` in `config/profile.yaml` (default `de`).

| File | Read by | What |
|---|---|---|
| `cv.md` | job-application-writer | what a strong CV looks like in this market (format, content, what to leave out) |
| `cover-letter.md` | job-application-writer | structure and style of the cover letter |
| `apply-strategy.md` | job-scan-apply | when a posting deserves a tailored application and when a template CV is enough |
| `market.md` | job-career-coach | how the market works for newcomers: language, entry routes, permits, typical pitfalls |

To add a country: copy `de/`, rewrite each file for that market, set `strategy.country` in the profile.
The rules are written as instructions for Claude; keep them short, concrete and checkable.
