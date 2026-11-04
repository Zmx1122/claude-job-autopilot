"""Export the Notion database to data/dashboard/data.json (aggregates) and data/dashboard/applications.json (rows for the artifact).

usage: python3 tools/dashboard_data.py
"""
import json, sys, os, requests, collections
from datetime import date, datetime
from common import *
env = load_env()
OUTDIR = os.path.join(DATA, 'dashboard'); os.makedirs(OUTDIR, exist_ok=True)
out = os.path.join(OUTDIR, 'data.json')
def txt(p): return ''.join(t['plain_text'] for t in p.get('rich_text', [])) if p else ''
def ttl(p): return ''.join(t['plain_text'] for t in p.get('title', [])) if p else ''
def sel(p): return (p.get('select') or {}).get('name', '') if p else ''
def dt(p): return ((p.get('date') or {}).get('start') or '') if p else ''
rows = notion_rows(env)
# funnel: every application passed through Applied; Confirmed/Interview/Offer are cumulative stages
ORDER = ['Applied', 'Confirmed', 'Interview', 'Offer']
def reached(r, stage):
    s = r['status']; i = ORDER.index(stage)
    if s in ORDER: return ORDER.index(s) >= i
    ev = r['events']
    if stage == 'Applied': return True
    if stage == 'Confirmed': return 'ats confirmation' in ev or 'interview' in ev or 'offer' in ev
    if stage == 'Interview': return 'interview' in ev or 'offer' in ev
    if stage == 'Offer': return 'offer' in ev
    return False
def ended(r): return r['status'] in ('Rejected', 'Withdrawn', 'Skipped')
# Sankey nodes: Applied -> Confirmed -> Interview -> Offer, with exits (Rejected/Withdrawn/Skipped) and "Waiting" (still open at that stage)
links = collections.Counter()
for r in rows:
    stages = [s for s in ORDER if reached(r, s)]
    for a, b in zip(stages, stages[1:]): links[(a, b)] += 1
    last = stages[-1]
    if ended(r): links[(last, r['status'])] += 1
    elif last != 'Offer': links[(last, f'Waiting at {last}')] += 1
by_week = collections.Counter(); by_week_plat = collections.defaultdict(collections.Counter)
for r in rows:
    if r['applied']:
        y, w, _ = date.fromisoformat(r['applied']).isocalendar(); k = f"{y}-W{w:02d}"
        by_week[k] += 1; by_week_plat[k][r['platform']] += 1
weeks = sorted(by_week)
# response time: days from applied to first rejection/interview event, from Events text
import re
resp = []
for r in rows:
    m = re.search(r'(\d\d-\d\d) (rejection|interview|offer)', r['events'])
    if m and r['applied']:
        try:
            d2 = date(int(r['applied'][:4]), int(m.group(1)[:2]), int(m.group(1)[3:])); d1 = date.fromisoformat(r['applied'])
            if 0 <= (d2 - d1).days <= 120: resp.append((d2 - d1).days)
        except ValueError: pass
# strategy review: interview rate by mode (tailored / template) and by posting age at application
def age_bucket(r):
    if not (r.get('posted') and r.get('applied')): return 'unknown'
    a = (date.fromisoformat(r['applied'][:10]) - date.fromisoformat(r['posted'][:10])).days
    return '≤1 day' if a <= 1 else '2–3 days' if a <= 3 else '4–7 days' if a <= 7 else '> 7 days'
def rates(key):
    g = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r['applied']:
            k = key(r); g[k][0] += 1; g[k][1] += reached(r, 'Interview')
    return {k: dict(applied=a, interview=i, rate=round(i / a, 3) if a else 0) for k, (a, i) in g.items()}
by_mode = rates(lambda r: r.get('mode') or 'unknown'); by_age = rates(age_bucket)
data = dict(generated=datetime.now().isoformat(timespec='minutes'), total=len(rows),
            by_status=dict(collections.Counter(r['status'] for r in rows)), by_platform=dict(collections.Counter(r['platform'] for r in rows)),
            funnel={s: sum(reached(r, s) for r in rows) for s in ORDER},
            sankey=[dict(source=a, target=b, value=v) for (a, b), v in links.items()],
            weekly=[dict(week=w, total=by_week[w], **by_week_plat[w]) for w in weeks],
            response_days=sorted(resp), by_mode=by_mode, by_age=by_age, open_rows=[r for r in rows if not ended(r)], rows=rows,
            notion_db=f"https://www.notion.so/{env['NOTION_DATABASE_ID'].replace('-', '')}")
json.dump(data, open(out, 'w'), ensure_ascii=False, indent=1)
print(f"{len(rows)} rows -> {out}; status={data['by_status']}; funnel={data['funnel']}; sankey links={len(links)}; weeks={len(weeks)}; response samples={len(resp)}")
print(f"interview rate by mode: {by_mode}\ninterview rate by posting age at application: {by_age}")

KEEP = ('id', 'title', 'company', 'city', 'platform', 'status', 'source', 'applied', 'last_email', 'events', 'url', 'evidence', 'notion_url', 'salary', 'mode', 'posted')
json.dump([{k: r.get(k, '') for k in KEEP} for r in rows], open(os.path.join(OUTDIR, 'applications.json'), 'w'), ensure_ascii=False)
print('rows for the artifact dataset ->', os.path.join(OUTDIR, 'applications.json'))
