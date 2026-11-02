"""Turn raw scan results into the shortlist table shown to the user.

usage: python3 tools/dedupe.py data/inbox/YYYY-MM-DD.json
Input: JSON list of jobs Claude collected while scanning, each with
  title, company, platform, url, city, salary, posted, apply_type (easy_apply | one_click | platform_form | external),
  needs (list, e.g. ["cv"], ["cv","cover_letter"], ["cv","degree_certificate"]), size (large|mid|startup|unknown), fit (0-100), why
Drops jobs already in Notion (same URL, or same company with a similar title), applies the profile filters
(blacklist, skip_title_keywords, exclude_titles, company_size, cover-letter rule), sorts by fit and prints a markdown table.
Writes the kept list to data/inbox/YYYY-MM-DD.shortlist.json.
"""
import json, sys, os
from common import load_env, load_profile, notion_rows, same_company, title_sim

src = sys.argv[1]
jobs = json.load(open(src))
prof = load_profile(); s = prof.get('search') or {}; rules = prof.get('rules') or {}
rows = notion_rows(load_env())
kept, dropped = [], []
def why_drop(j):
    t = (j.get('title') or '').lower(); c = j.get('company') or ''
    if any(b.lower() in c.lower() for b in s.get('blacklist_companies', []) if b): return 'blacklisted company'
    if any(k.lower() in t for k in s.get('skip_title_keywords', []) + s.get('exclude_titles', []) if k): return 'title filter'
    if s.get('company_size') == 'established' and j.get('size') == 'startup': return 'startup'
    if 'cover_letter' in (j.get('needs') or []) and rules.get('cover_letter_required', 'skip') == 'skip': return 'requires cover letter'
    for r in rows:
        if j.get('url') and r['url'] and r['url'].split('?')[0] == j['url'].split('?')[0]: return f"already in tracker ({r['status']})"
        if same_company(c, r['company']) and (title_sim(j.get('title'), r['title']) or 0) >= 0.8: return f"already in tracker ({r['status']})"
    return None
seen = set()
for j in jobs:
    key = (j.get('company', '').lower(), j.get('title', '').lower())
    if key in seen: dropped.append((j, 'duplicate in scan')); continue
    seen.add(key)
    w = why_drop(j)
    (dropped.append((j, w)) if w else kept.append(j))
kept.sort(key=lambda j: -(j.get('fit') or 0))
cap = int(s.get('max_applications_per_day') or 10)
print(f'{len(jobs)} scanned → {len(kept)} new candidates (daily cap {cap}).\n')
print('| # | Company | Title | Platform | How to apply | Needs | Salary | Fit | Why |')
print('|---|---|---|---|---|---|---|---|---|')
for i, j in enumerate(kept, 1):
    print(f"| {i} | {j.get('company','')} | [{j.get('title','')}]({j.get('url','')}) | {j.get('platform','')} | {j.get('apply_type','')} | "
          f"{', '.join(j.get('needs') or ['cv'])} | {j.get('salary') or '–'} | {j.get('fit','')} | {j.get('why','')} |")
if dropped:
    print('\nDropped: ' + '; '.join(f"{j.get('company','?')} – {j.get('title','')[:40]} ({w})" for j, w in dropped))
json.dump(kept, open(src.replace('.json', '.shortlist.json'), 'w'), ensure_ascii=False, indent=1)
