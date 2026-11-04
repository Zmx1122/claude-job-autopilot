"""Turn raw scan results into the shortlist table shown to the user, with a Mode per job (🎯 tailored / 📄 template).

usage: python3 tools/dedupe.py data/inbox/YYYY-MM-DD.json [--offline]
Input: JSON list of jobs Claude collected while scanning, each with
  title, company, platform, url, city, salary, posted (YYYY-MM-DD, or the platform's text such as "vor 3 Tagen" / "2 days ago"),
  reposted (true if the platform marks it reposted / erneut gepostet), apply_type (easy_apply | one_click | platform_form | external),
  needs (list, e.g. ["cv"], ["cv","cover_letter"], ["cv","degree_certificate"]), size (large|mid|startup|unknown), fit (0-100), why
Drops jobs already in Notion (same URL, or same company with a similar title), applies the profile filters
(blacklist, skip_title_keywords, exclude_titles, company_size, cover-letter rule, fit below strategy.fit_medium),
decides the Mode with the table in standards/<country>/apply-strategy.md, sorts by fit and prints a markdown table.
Writes the kept list (with mode, mode_reason, age_days) to data/inbox/YYYY-MM-DD.shortlist.json.
--offline skips the Notion lookup (testing).
"""
import json, os, re, sys
from datetime import date, timedelta
from common import load_env, load_profile, notion_rows, same_company, title_sim

UNITS = {'h': 0, 'hour': 0, 'stunde': 0, 'minute': 0, 'min': 0, 'day': 1, 'tag': 1, 'week': 7, 'woche': 7, 'month': 30, 'monat': 30}


def age_days(posted, today=None):
    """Days since posting from an ISO date or a platform phrase; None when unknown."""
    today = today or date.today()
    if posted in (None, ''):
        return None
    if isinstance(posted, (int, float)):
        return int(posted)
    p = str(posted).strip().lower()
    m = re.match(r'(\d{4}-\d{2}-\d{2})', p)
    if m:
        return max(0, (today - date.fromisoformat(m.group(1))).days)
    if re.search(r'just now|today|heute|gerade|soeben|neu\b|new\b', p):
        return 0
    if re.search(r'yesterday|gestern', p):
        return 1
    m = re.search(r'(\d+)\+?\s*(h|hour|stunde|minute|min|day|tag|week|woche|month|monat)', p)
    if m:
        return int(m.group(1)) * UNITS[m.group(2)]
    m = re.search(r'\b(a|an|one|ein|einem|einer)\s+(day|tag|week|woche|month|monat)', p)
    if m:
        return UNITS[m.group(2)]
    return None


def decide(age, familiar, fit, dream, hi, med):
    """Mode from the decision table (standards/de/apply-strategy.md). Returns (mode, reason)."""
    if dream:
        return 'tailored', 'dream company / role'
    high = fit >= hi
    if age is None:
        return 'template', 'posting date unknown'
    if age == 0:
        return ('template', '≤24h but seen before') if familiar else ('tailored', '≤24h, new')
    if age <= 3:
        if high and not familiar:
            return 'tailored', f'{age}d old, high fit, new'
        return 'template', f'{age}d old' + (', seen before' if familiar else ', medium fit')
    if age <= 7:
        return ('tailored', f'{age}d old, high fit') if high else ('template', f'{age}d old, medium fit')
    return 'template', f'{age}d old'


def main():
    src = sys.argv[1]
    offline = '--offline' in sys.argv
    jobs = json.load(open(src))
    prof = load_profile(); s = prof.get('search') or {}; rules = prof.get('rules') or {}; st = prof.get('strategy') or {}
    hi, med = int(st.get('fit_high', 80)), int(st.get('fit_medium', 60))
    cap_t = int(st.get('tailored_per_day', 3)); fam_n = int(st.get('familiar_after', 3))
    dream_co = [d.lower() for d in st.get('dream_companies') or [] if d]
    dream_kw = [d.lower() for d in st.get('dream_title_keywords') or [] if d]
    letter_rule = rules.get('cover_letter_required', 'draft')
    rows = [] if offline else notion_rows(load_env())
    recent = [r for r in rows if (r.get('first_seen') or '') >= str(date.today() - timedelta(days=30))]

    def why_drop(j):
        t = (j.get('title') or '').lower(); c = j.get('company') or ''
        if any(b.lower() in c.lower() for b in s.get('blacklist_companies', []) if b): return 'blacklisted company'
        if any(k.lower() in t for k in s.get('skip_title_keywords', []) + s.get('exclude_titles', []) if k): return 'title filter'
        if s.get('company_size') == 'established' and j.get('size') == 'startup': return 'startup'
        if 'cover_letter' in (j.get('needs') or []) and letter_rule == 'skip': return 'requires cover letter'
        if j.get('fit') is not None and j['fit'] < med and not any(d in c.lower() for d in dream_co): return f"fit {j['fit']} < {med}"
        for r in rows:
            if j.get('url') and r['url'] and r['url'].split('?')[0] == j['url'].split('?')[0]: return f"already in tracker ({r['status']})"
            if same_company(c, r['company']) and (title_sim(j.get('title'), r['title']) or 0) >= 0.8: return f"already in tracker ({r['status']})"
        return None

    def familiar(j):
        c = j.get('company') or ''
        if j.get('reposted'): return True
        if any(same_company(c, r['company']) and (title_sim(j.get('title'), r['title']) or 0) >= 0.5 for r in rows): return True
        return sum(same_company(c, r['company']) for r in recent) >= fam_n

    kept, dropped, seen = [], [], set()
    for j in jobs:
        key = (j.get('company', '').lower(), j.get('title', '').lower())
        if key in seen: dropped.append((j, 'duplicate in scan')); continue
        seen.add(key)
        w = why_drop(j)
        if w: dropped.append((j, w)); continue
        j['age_days'] = age_days(j.get('posted'))
        c, t = (j.get('company') or '').lower(), (j.get('title') or '').lower()
        dream = any(d in c for d in dream_co) or any(d in t for d in dream_kw)
        j['familiar'] = familiar(j)
        j['mode'], j['mode_reason'] = decide(j['age_days'], j['familiar'], j.get('fit') or 0, dream, hi, med)
        kept.append(j)
    kept.sort(key=lambda j: (j['mode'] != 'tailored', -(j.get('fit') or 0)))
    n = 0
    for j in kept:
        if j['mode'] == 'tailored':
            n += 1
            if n > cap_t and 'dream' not in j['mode_reason']:
                j['mode'], j['mode_reason'] = 'template', j['mode_reason'] + f'; tailored cap {cap_t}/day'
    kept.sort(key=lambda j: (j['mode'] != 'tailored', -(j.get('fit') or 0)))
    cap = int(s.get('max_applications_per_day') or 10)
    icon = {'tailored': '🎯 tailored', 'template': '📄 template'}
    print(f"{len(jobs)} scanned → {len(kept)} new candidates (daily cap {cap}; "
          f"{sum(j['mode'] == 'tailored' for j in kept)} tailored, {sum(j['mode'] == 'template' for j in kept)} template).\n")
    print('| # | Mode | Company | Title | Platform | Posted | How to apply | Needs | Salary | Fit | Why |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for i, j in enumerate(kept, 1):
        needs = ', '.join(x + (' (draft)' if x == 'cover_letter' else '') for x in (j.get('needs') or ['cv']))
        posted = '?' if j['age_days'] is None else ('today' if j['age_days'] == 0 else f"{j['age_days']}d")
        print(f"| {i} | {icon[j['mode']]} · {j['mode_reason']} | {j.get('company','')} | [{j.get('title','')}]({j.get('url','')}) | "
              f"{j.get('platform','')} | {posted} | {j.get('apply_type','')} | {needs} | {j.get('salary') or '–'} | {j.get('fit','')} | {j.get('why','')} |")
    if dropped:
        print('\nDropped: ' + '; '.join(f"{j.get('company','?')} – {j.get('title','')[:40]} ({w})" for j, w in dropped))
    json.dump(kept, open(src.replace('.json', '.shortlist.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
