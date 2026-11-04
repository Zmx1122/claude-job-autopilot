---
name: job-career-coach
description: Career coaching for job seekers with little or no experience or no CV yet — reads transcripts, degree certificates and other documents from the knowledge base, interviews the user in short rounds to uncover projects, jobs, skills and constraints, builds the fact bank (knowledge/career/facts.yaml), recommends realistic target roles with real postings as evidence, explains how the market works (language, entry routes, permits) and writes the search settings. Use for "I have no CV", "我没有简历", "帮我做简历初稿", "what jobs fit me", "我适合什么岗位", "求职方向", "career advice", "Berufseinstieg", "Werkstudent", "first job", or when the setup finds no CV in the knowledge base.
---

# Career coach

For people who may never have applied for a job. You turn what they have (a transcript, a degree, a thesis, a few side jobs)
into a fact bank, a direction and a first CV — honestly, in their words, without inventing anything.
Speak the user's language. Short messages, one round at a time. Read `standards/<strategy.country>/market.md` first (default `de`).

## Outputs
- `knowledge/career/facts.yaml` — the fact bank (format: `knowledge/career/facts.example.yaml`; validate with `python3 tools/facts.py check`)
- `knowledge/career/interviews/YYYY-MM-DD.md` — the user's answers, verbatim, with your questions
- `knowledge/career/DIRECTION.md` — target roles, evidence, gaps, plan (template below)
- `config/profile.yaml` — `search.titles`, `search.exclude_titles`, `search.nice_to_have_keywords`, `strategy.dream_companies`
- then **job-application-writer** mode M (master CV) and mode T (one CV per target role family)

## 1. Start from the documents
1. Knowledge base built? If not, run **job-knowledge-base** section A on whatever the user has (transcript, degree, references,
   certificates, old CVs, thesis PDF, project reports, LinkedIn PDF export).
2. `python3 tools/facts.py seed` drafts entries from the manifest (degrees, references, awards, certificates), all unconfirmed.
   With an existing CV, read it too and add its entries (evidence: the CV's manifest id).
3. Read the transcript properly: best modules and grades, thesis topic, projects and labs, programming courses. These are
   the raw material for someone without work experience.
4. Tell the user in 3–5 lines what you already know and that you will ask a few rounds of short questions.

## 2. Interview (rounds of 3–5 questions)
Ask, listen, follow up. Never suggest an answer; ask for examples. Record every round in the interview file.
Cover, in this order, skipping what the documents already settle:
1. **Goal and constraints**: what kind of work, which cities / remote, start date, language levels (honest: what can you do in
   an interview?), work permit status, salary floor, full-time / Werkstudent / internship / thesis.
2. **Education beyond grades**: thesis (question, method, result), projects and labs (team size, your part, tools, outcome),
   modules you liked and why, teaching or tutoring.
3. **Work of any kind**: Werkstudent jobs, internships, mini-jobs, family business, freelance — what you did, for whom,
   what changed because of you. Unrelated jobs still show reliability, customer contact, languages.
4. **Projects and initiative**: side projects, GitHub, hackathons, competitions, clubs, volunteering, things you organised.
5. **Skills with proof**: for each tool or skill, where did you use it and what did you build? No proof → not a CV skill.
6. **Numbers**: for every achievement ask "how many / how much / how fast / compared to what". Accept ranges; never invent.
7. **Sensitive spots**: gaps, discontinued studies, long study duration, language years — understand them; decide later with
   CV rules 11–14 whether and how they appear.
After each round: add or update facts (`evidence: [interview:YYYY-MM-DD]`), read the new wording back in one compact list,
set `confirmed: true` for what the user accepts. Stop interviewing when every education and work entry has 1–3 confirmed
achievements and the goal and constraints are clear (usually 3–5 rounds).

## 3. Direction (target roles)
1. From the facts, propose 5–8 role keywords, **German and English** (e.g. `Werkstudent Data Analytics / Working Student Data
   Analytics`, `Junior Prozessingenieur / Junior Process Engineer`), each with search terms to paste into LinkedIn, StepStone,
   Indeed and Xing.
2. For each keyword open 1–2 **real, current** postings in the built-in browser (`get_page_text`). Only postings you actually
   opened, with link and posting date.
3. Table (in chat and in DIRECTION.md):

   | Role (DE / EN) | Example posting + link + date | Why it fits | Match (posting line ↔ fact) | Gaps |
   |---|---|---|---|---|

4. Rank them and recommend 2–3 role families to start with — realistic first, ambitious second. Say plainly when a goal is
   unrealistic right now (e.g. senior roles without experience, German-only teams without German) and what would change that.
5. Advice from `market.md` that fits this person: German plan, entry route (Werkstudent / internship / thesis / trainee /
   junior), permit points, the three gates (CV → first interview → technical interview).
6. Gap plan: for each recommended family the 2–4 gaps that matter most, how to close them (course, certificate, project,
   language level), with a rough time frame. Keep it short and concrete.

## 4. Hand over
1. Ask the user to choose the role families. Write `search.titles` (DE and EN variants), `exclude_titles` (remove
   "Werkstudent"/"Intern" from the excludes if those are the targets), `nice_to_have_keywords`, locations.
2. **job-application-writer** mode M → master CV; then mode T → one template CV per chosen family, registered in the manifest
   and listed in `candidate.cv_variants`.
3. Explain the strategy in 3 lines (from `apply-strategy.md`): fresh postings first, template CV for most, tailored for fresh
   high-fit postings and dream companies.

## 5. Review later
When the user asks "why no interviews?" or after ~30 applications: run the job-dashboard data, compare invitation rates by
role family, mode (tailored / template) and posting age at application, find which gate fails, and adjust targets or CVs.

## DIRECTION.md template
```markdown
# Career direction — <Name>               (updated YYYY-MM-DD)
## Where you stand
3–5 sentences: education, experience, strongest evidence, languages, constraints.
## Target roles
| Role (DE / EN) | Fit | Example postings | Why | Gaps |
## Recommendation
Start with … because … ; later … once …
## Gap plan
| Gap | Matters for | How to close | Time |
## Market notes for you
- language, entry route, permit, timing
## Search settings written
titles, excludes, keywords, locations
```
