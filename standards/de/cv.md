# Germany · CV standard (Lebenslauf / CV)

Apply these rules to every CV you write or edit for the German market unless the user says otherwise.
Origin: reverse-engineered from CVs that won interviews and an offer in 2025–2026, plus the problems found when reviewing
other candidates' CVs. Numbers in brackets are referenced by `tools/doc_check.py` and the writer skill.

## Format
1. **Length**: under 10 years of experience → 1 page, never more than 2. Reverse chronological. Every entry dated to the
   month (`MM/YYYY` or `Mon YYYY`, one style throughout).
2. **Language** = the posting's language. A German posting gets a German CV unless it says English is fine.
3. **Header**: name · a title aimed at the target role · city · phone · email · LinkedIn (clickable) · languages with CEFR level
   (e.g. `Deutsch C1`). Photo, date of birth and marital status are optional, not expected.
4. **Machine-readable PDF**: real text, one column, standard section headings, no text inside images, no tables for layout.
   Many recruiters read the ATS-parsed version — two-column templates come out interleaved and unreadable.
   File name `FirstName-LastName-CV-Company.pdf`.

## Content
5. **Summary**, 3–4 lines: who I am + core skills + the 1–2 results most relevant to the posting; the posting's keywords
   appear naturally.
6. **Each position**: role · organisation · from–to · city. Small or foreign organisations get one line saying what they do
   and how big they are.
7. **2–4 bullets per position**, each = action verb + what was done + measurable result (users, time saved, accuracy, scale).
   No number available → give a range or adoption ("still in use", "rolled out to 3 plants"). Never invent a number.
8. **Skills grouped by category**, only skills the experience section proves. No hollow qualifiers
   ("proficient", "professional", "expert", "熟练") — show the level through the bullets.
9. **Each achievement appears once.** Do not repeat the same result under experience, achievements and publications.
10. **Education**: degree · university · grade. Non-German grades state the scale or the German equivalent. Universities
    unknown in Germany get one line of positioning (e.g. "top-tier '985' university").
11. **Degree status is explicit**: ongoing / completed / discontinued — especially a PhD. Never make HR guess.
    A discontinued degree is judged against the posting:
    - **plus** — discontinued PhD with strong papers or projects; or credits nearly complete, good grades, skills that match
      → write it positively, lead with the output;
    - **neutral** — discontinued PhD with little research output but relevant teaching or projects → keep it, lead with
      teaching and projects;
    - **minus** — few credits, poor grades, unrelated (e.g. a programme taken only to look better for a TU9 application)
      → handle with rule 14.
12. **No obligation to be gap-free (lückenlos)**. German postings do not require it. Do not pad gaps with short entries that
    hurt (rule 14); prepare one sentence that explains the gap in an interview.

## Choosing what goes in
13. **Judge every entry and every bullet against the posting before writing**: plus, neutral or minus. For contested ones
    list pro and con, propose keep / shorten / drop with a reason, and decide **together with the user** before generating.
14. Entries that could count against the candidate, by duration:
    - under 6 months → leave out;
    - 6–12 months → one line (role · organisation · dates), no bullets;
    - over 1 year → first interview the user for highlights and bullets that could count in their favour, then write it
      as briefly as possible so no gap appears.
15. **Signal over volume**: a recruiter scans for about 20 keywords. 25 lines hitting 18 of them beats 50 lines hitting 20.
    Cut anything that is neither required nor a clear strength. Do not volunteer negatives (years spent learning a language,
    "graduating in 5 months" on a working-student application).

## Self-check
16. Dates, titles and numbers are identical in the CV and the cover letter.
17. Every line survives an interview follow-up question. If the user cannot explain it, delete it.
18. No salary expectation in the CV.

## Wording for screeners (HR, recruiters, ATS) — read these before writing any bullet
The first reader is usually a recruiter or an ATS filter, not an engineer. The engineer reads the CV second. Write so both are served.

19. **Never delete a name — explain it.** Project names, method and algorithm names, model names, tools, paper and award titles stay
    in the CV: they are what a reader can look up and what an interviewer asks about. What is missing is the plain-language
    category, so add it next to the name (general term first with the name in brackets, or the name followed by a short appositive):
    - models: "fine-tuned Qwen-7B" → "fine-tuned an open-source LLM (Qwen 7B, published on Hugging Face)"; Llama, Mistral, Gemma likewise.
      Never a bare model name plus size.
    - algorithms and methods: "Double DQN" → "reinforcement-learning algorithm (Double DQN)"; "LoRA" → "parameter-efficient
      fine-tuning method (LoRA)"; "DPO" → "preference-based model-alignment method (DPO)".
    - project, programme and paper names (e.g. "DSL4DPiFS", "MiProcess2Twin", "DFG SPP 2422"): keep them and say what they are —
      "DSL4DPiFS, a graphical modelling language for data pipelines in forming systems", "MiProcess2Twin, a digital-twin project for
      construction processes (VDI/VDE-IT Bayern)", "DFG-funded research programme SPP 2422".
    - Terms every recruiter in the field already searches for (LLM, RAG, Python, Azure, Kubernetes, CI/CD) need no gloss.
    - Test: could a recruiter who has never seen this name tell what kind of thing it is (model, method, tool, project, paper)? If not, add the category.
    - The descriptor must be **true and verifiable**: take it from the fact bank or the source. "Open-source" only if the licence is open,
      otherwise "open-weight"; "on Hugging Face" only if the model really is published there. If unsure, ask the user. Never guess a category.
20. **Say each technical term once per position.** When several bullets or projects share the same stack, lift the shared terms into
    **one lead line** and let the sub-bullets carry only what differs: use case or context, scale, result.
    ```
    Developed LLM applications with LangChain, Llama and LLM-as-judge evaluation:
      – customer-call summaries for sales teams: satisfaction 60 % → 95 %
      – voice assistant for appointment booking: live for 3,000 daily users
    ```
    not "Project 1 … (LangChain, Llama, LLM-as-judge). Project 2 … (LangChain, Llama, LLM-as-judge)".
    - Test: a term that appears in 2 or more bullet lines of the same position is lifted into the lead line. A term that belongs to one use case only stays in that sub-bullet.
    - The lead line is a full sentence a recruiter can read on its own: action verb + object + the shared stack in general words.
    - Sub-bullets are short (one line each) and start with the use case, not with a repeated verb or tool list.
    - The summary and the skills list may name a term again (ATS keyword match); the bullets of one position never repeat it.
21. **Rules 19 and 20 do not remove keywords.** The posting's keywords (rule 5, rule 15) appear once in the lead line or the skills list. Fewer repeats, same coverage.
22. **Facts stay facts.** Rewording for readability never adds a skill, number or duration (rule 7). The fact bank keeps its precise engineer wording; only the CV text is rewritten.

