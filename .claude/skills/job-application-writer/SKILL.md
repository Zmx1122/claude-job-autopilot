---
name: job-application-writer
description: Write and tailor CVs and cover letters (Lebenslauf, Anschreiben, Motivationsschreiben) from the user's fact bank — a master CV, one template CV per role family, or a CV plus cover letter tailored to one posting with a requirement match table, gap questions, plus/minus judgement of every entry, change list and a consistency check. Use for "write my CV", "tailor my CV", "简历", "改简历", "优化简历", "求职信", "动机信", "Anschreiben", "cover letter", "does my CV fit this job", "检查岗位匹配度", or when job-scan-apply marks a job 🎯 tailored or a form requires a cover letter.
---

# Application writer

Every document is built from **`knowledge/career/facts.yaml`** (the fact bank) and checked against the country standard in
`standards/<strategy.country>/` (`cv.md`, `cover-letter.md`; default `de`). Read both standards before writing; they are the
rules, this skill is the procedure. Rule numbers below refer to them.

## Ground rules (all modes)
1. **No invented facts.** Every line comes from a `confirmed: true` fact. New information from the user goes into the fact bank
   first: write their answer verbatim to `knowledge/career/interviews/YYYY-MM-DD.md`, add or update the fact with
   `evidence: [interview:YYYY-MM-DD]`, read the wording back, set `confirmed: true` when they agree. Then use it.
2. **Exact numbers and durations.** Quote durations from `python3 tools/facts.py durations` (never round "2 years 3 months"
   up to "two and a half years"). If the user chose a wording for an entry (`duration_wording`, e.g. "about 2.5 years"),
   use exactly that, in every document. No number available → range or adoption, never a guess (CV rule 7).
3. **The user decides contested content.** Plus/minus judgement and every cut that changes the story is proposed, not done (CV rule 13).
4. **Language** = the posting's language (CV rule 2). Writing German: natural business German, not translated English.
5. **Never** put a salary in a CV; in a letter only when the posting asks for a Gehaltsvorstellung, with the user's figure.
6. Generated files and drafts stay on this Mac (`knowledge/` and `data/` are git-ignored).
7. Before using the fact bank: `python3 tools/facts.py check`. Unconfirmed facts are not usable; open questions that affect the
   document are asked first, all at once.
8. **Write for the screener first** (CV rules 19–22): the first reader is a recruiter or an ATS filter, not an engineer.
   Run the **wording pass** below on every CV before rendering.

## Wording pass (every CV, every mode, before rendering)
The fact bank keeps precise engineer wording. The CV text is a rewrite of it for a non-engineer reader, with no new facts.
1. **Group by position.** For each position, list the technical terms of all its facts. Terms that occur in two or more facts are
   *shared stack*. Do not write one bullet per project with the stack repeated in each.
2. **Lead line + sub-bullets** (CV rule 20). Shared stack goes once into a lead line that reads as a sentence on its own, the
   use cases follow as short sub-bullets with context and result only:
   ```yaml
   - text: "Developed LLM applications with LangChain, Llama and LLM-as-judge evaluation:"
     sub:
       - "customer-call summaries for sales teams: satisfaction 60 % → 95 %"
       - "appointment-booking assistant: live for 3,000 daily users"
   ```
   Not: "Project 1 … (LangChain, Llama, LLM-as-judge). Project 2 … (LangChain, Llama, LLM-as-judge)."
   A bullet that has only one use case needs no sub-bullets. A term that belongs to a single use case stays in that sub-bullet.
3. **Never delete a name, explain it** (CV rule 19): project, method, algorithm, model, tool and paper names stay; the plain-language
   category goes next to them — "reinforcement-learning algorithm (Double DQN)", "open-source LLM (Qwen 7B, published on Hugging
   Face)", "DSL4DPiFS, a graphical modelling language for data pipelines in forming systems". Terms recruiters already search for
   (LLM, RAG, Python, Azure) stay bare. The descriptor must be true: take it from the fact bank or the source; "open-source" only if
   the licence is open, otherwise "open-weight"; "on Hugging Face" only if it is published there; if you are not sure what a term is,
   ask the user instead of guessing.
4. **Keep the keywords** (rule 21): the posting's keywords appear once, in the lead line or the skills list.
5. Read the result as a recruiter who knows the job family but not the tools. Any line they could not explain in one sentence is rewritten.

## Files
```
knowledge/career/facts.yaml            fact bank (single source of truth)
knowledge/career/interviews/DATE.md    the user's answers, verbatim
knowledge/career/cvs/<id>.yaml         content of master and template CVs → knowledge/library/cv/<File>.pdf (registered in manifest)
data/applications/<YYYY-MM-DD>_<company>_<title>/
    jd.md        the posting: full text, URL, posted date, language, contact person, reference number
    match.md     requirement table, gap questions and answers, plus/minus decisions
    cv.yaml, letter.yaml                         content
    <First>-<Last>-CV-<Company>.pdf, <First>-<Last>-Anschreiben-<Company>.pdf (or -CoverLetter-)
    changes.md   what changed vs the base CV, why, which posting line; source URL of the company fact used in the letter
```
Render: `python3 tools/doc_render.py cv|letter <yaml> --out <pdf> [--max-pages 1]` — it prints the PDF path, checks that
every line is in the text layer in reading order (what an ATS reads) and writes a PNG preview. **Look at the preview**
(dual review: text check passed is not enough — check layout, line breaks, one page).
Check: `python3 tools/doc_check.py --cv <pdf> --cv-yaml <the cv.yaml it was rendered from> [--letter <pdf>] --facts knowledge/career/facts.yaml --keywords "a|a-variant,b,c" [--company X]`.
`--cv-yaml` switches on the screener-wording checks (bare model names, algorithms without a general term, unexplained codenames, a term repeated across the bullets of one position).
Fix every ❌; mention ⚠️ items to the user only if they are real. The content YAML formats are in the docstring of `tools/doc_render.py`.

## Mode M · Master CV (first CV, or rebuild)
1. Fact bank empty or thin → run **job-career-coach** first (interview).
2. Draft `knowledge/career/cvs/cv-master-<lang>.yaml`: all strong facts, 1–2 pages, standard order
   (header · summary · experience · skills · awards · education · publications if relevant); run the **wording pass**.
3. Render, look, check. Show the PDF path and a 5-line summary of choices (what was left out and why).
4. After the user's OK: render to `knowledge/library/cv/CV_Master_<LANG>_<YYYY>.pdf` with `--register cv-master-<lang>`.

## Mode T · Template CV per role family (for 📄 template applications)
One CV per role family the user targets (from `search.titles` / `knowledge/career/DIRECTION.md`), e.g. "Conversational AI",
"Data / Digitalization". For each family:
1. Collect 10–20 typical postings' requirements (open 3–5 real postings; note the recurring keywords, DE and EN).
2. Select and order facts for that family; summary and headline aimed at it; keywords from the postings appear naturally; run the **wording pass** (CV rules 19–22).
3. Render to `knowledge/library/cv/CV_<Family>_<LANG>_<YYYY>.pdf`, `--register cv-<family>-<lang> --use-for "<title keywords>"`.
4. Update `candidate.cv_variants` in `config/profile.yaml` (file + use_for). The scan-apply skill picks variants by `use_for`.
Template CVs are not edited per posting. Rebuild them when the fact bank changes materially.

## Mode J · Tailored application for one posting (🎯)
Steps 2–4 are a conversation; keep each message short and batch questions. When several tailored jobs are open at once
(from a scan), ask the questions for **all of them in one round**.
1. **Intake.** Open the posting (built-in browser, `get_page_text`), write the text to a scratch file and run
   `python3 tools/jd_snapshot.py --url … --company … --title … --text-file <file>`: it creates the application folder with
   `jd.md` (text + header) and `jd.pdf` / `page.pdf` (copies to keep). Add to `jd.md`'s header: posted date, language,
   contact person, reference number, upload slots if visible. Pick the base CV: the variant whose `use_for` fits best.
2. **Match table** (`match.md`, and show it):

   | Requirement (from the posting) | Must / Nice | Status ✅ ⚠️ ❌ | Evidence (fact id → wording) |
   |---|---|---|---|

   Then 3 lines: overall fit (high / medium / low), the 3 strongest matches, the 2 biggest gaps.
3. **Gap questions.** For each ⚠️ / ❌ ask 3–5 questions per round that help the user remember related experience
   (projects, courses, thesis, side work, tools used once). Do not suggest answers. Follow up until each gap is settled:
   *can be covered* (new fact, confirmed) / *only weakly* (mention lightly or not at all) / *really missing* (leave out; consider
   addressing it in the letter as a learning plan only if it is a must-have).
4. **Plus / minus pass** (CV rules 11, 13, 14): one table over every entry and bullet of the base CV —
   `item | plus / neutral / minus for THIS posting | proposal (keep / shorten / move / drop) | reason`.
   Contested items get pro and con. Wait for the user's decisions.
5. **Write `cv.yaml`**: headline and summary aimed at the posting; bullets reordered so the posting's top requirements are
   answered first; the posting's keywords (exact spelling, DE/EN as in the posting) appear in summary and bullets where true;
   1 page under 10 years of experience; run the **wording pass** (shared stack once in a lead line, general descriptors for rare names).
   Render to `<First>-<Last>-CV-<Company>.pdf`.
6. **Cover letter** when the form has a cover-letter slot, the form requires one, or `strategy.cover_letter: always`:
   - one verifiable company fact for paragraph 1 — open the company's site or newsroom, record the URL in `changes.md`;
   - paragraphs per letter rules 5–9; style samples in the knowledge base (`kind: cover_letter`) show the user's voice —
     reuse their tone, never their sentences for another company;
   - 300–450 words; render to `<First>-<Last>-Anschreiben-<Company>.pdf` (German) or `-CoverLetter-` (English).
7. **Check**: `doc_check.py` with the posting's 3–5 most important keywords (with DE/EN variants), `--company` and `--cv-yaml cv.yaml`.
   Fix every ❌ (durations, numbers, missing keywords) and re-render.
8. **Review with the user**: show the PDF paths, the change list (`what changed | why | posting line`) and any ⚠️ worth a
   decision. Apply their edits. Approval of the text is required before upload.
9. Hand back to job-scan-apply (upload slot ← file), or tell the user where the files are. The application's Notes get
   `mode: tailored; cv: <file>; letter: yes/no`.

## Mode R · Reuse check (quick)
"Does my CV fit this job?" / "Which CV should I use?": steps 1–2 of mode J, then name the closest existing CV and at most
5 changes that would make it fit. Offer mode J only if the fit is high and the posting is fresh (see `standards/<c>/apply-strategy.md`).

## Cover letter only (template applications whose form requires one)
`rules.cover_letter_required: draft` → write a short letter (letter rules, 250–350 words) from the template CV's facts and one
company fact; same check and approval as mode J step 6–8. `skip` → the job is skipped (scan-apply handles this).
