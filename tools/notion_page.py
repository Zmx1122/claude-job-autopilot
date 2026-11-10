"""Rebuild the Dashboard section at the TOP of the Notion Job Search page (run dashboard_data.py and charts_png.py first).

Layout, top to bottom (user decision 2026-11-10):
  Dashboard heading · callout "Total applications: N" · link to the interactive dashboard
  two columns: stage pie | flow between stages
  applications per week (full width, on its own)
  "Which applications get interviews" table
  Database heading · the Job Applications database (stays at the bottom)
The section is everything between the "Dashboard" heading and the database; it is replaced on every run. The Notion API
cannot move the database block, so on an old page (database first, dashboard below it) the heading right above the database
becomes the "Dashboard" heading and a new "Database" heading is inserted right above the database.
No Mermaid code blocks (Notion shows their source code). For wider charts turn on ••• → Full width on the page once.
"""
import json, os, sys, requests
import datetime as _dt
from common import *
env = load_env(); H = {'Authorization': f"Bearer {env['NOTION_TOKEN']}", 'Notion-Version': '2022-06-28'}; HJ = {**H, 'Content-Type': 'application/json'}
PAGE = env['NOTION_PARENT_PAGE_ID']; DASH_URL = env.get('DASHBOARD_URL', '')
OUTDIR = os.path.join(DATA, 'dashboard')
d = json.load(open(os.path.join(OUTDIR, 'data.json')))
MARK = 'Dashboard'
def upload(path):
    name = os.path.basename(path)
    fu = requests.post('https://api.notion.com/v1/file_uploads', headers=HJ, json={'filename': name, 'content_type': 'image/png'}).json()
    r = requests.post(f"https://api.notion.com/v1/file_uploads/{fu['id']}/send", headers=H, files={'file': (name, open(path, 'rb'), 'image/png')})
    if r.status_code != 200: raise SystemExit(f'upload failed {r.status_code} {r.text[:200]}')
    return fu['id']
def t(s, **a): return {'type': 'text', 'text': {'content': s}, **({'annotations': a} if a else {})}
# 1. find the database and the current dashboard section
blocks, cursor = [], None
while True:
    r = requests.get(f'https://api.notion.com/v1/blocks/{PAGE}/children', headers=H, params={'page_size': 100, **({'start_cursor': cursor} if cursor else {})}).json()
    blocks += r['results']
    if not r.get('has_more'): break
    cursor = r['next_cursor']
def text_of(b): return ''.join(x['plain_text'] for x in (b.get(b['type'], {}).get('rich_text') or []))
def delete(b): requests.delete(f"https://api.notion.com/v1/blocks/{b['id']}", headers=H)
db_i = next((i for i, b in enumerate(blocks) if b['type'] == 'child_database'), None)
mk_i = next((i for i, b in enumerate(blocks) if b['type'] == 'heading_1' and text_of(b) == MARK), None)
removed = 0; anchor = None; need_heading = True
if mk_i is not None and (db_i is None or mk_i < db_i):          # current layout: dashboard above the database
    anchor = blocks[mk_i]['id']; need_heading = False
    for b in blocks[mk_i + 1:db_i if db_i is not None else len(blocks)]: delete(b); removed += 1
else:
    if mk_i is not None:                                         # old layout: remove the old section below the database
        end = next((j for j in range(mk_i + 1, len(blocks)) if blocks[j]['type'] in ('heading_1', 'child_database')), len(blocks))
        for b in blocks[mk_i:end]: delete(b); removed += 1
    if db_i:                                                     # put the dashboard right above the database
        prev = blocks[db_i - 1]
        if prev['type'] == 'heading_1':                          # the "Database" heading becomes the dashboard heading
            requests.patch(f"https://api.notion.com/v1/blocks/{prev['id']}", headers=HJ, json={'heading_1': {'rich_text': [t(MARK)]}})
            need_heading = False
        anchor = prev['id']
    elif db_i == 0:
        print('note: the database is the first block of the page; the API cannot insert above it, so the dashboard goes below it')
# 2. build the new section
s = d['by_status']; f = d['funnel']; total = d['total']; open_n = len(d['open_rows']); rej = s.get('Rejected', 0)
not_sent = s.get('Skipped', 0) + s.get('Shortlisted', 0) + s.get('Seen', 0)   # 放弃投递 / 待定: tracked, never sent
sent = total - not_sent
med = d['response_days'][len(d['response_days']) // 2] if d['response_days'] else None
if not d['total']:
    raise SystemExit('No applications in the database yet; the dashboard is built after the first rows exist.')
today = _dt.date.today().isoformat()
since = min((r['applied'] for r in d['rows'] if r.get('applied')), default=today)
children = [{'object': 'block', 'type': 'heading_1', 'heading_1': {'rich_text': [t(MARK)]}}] if need_heading else []
children += [
 {'object': 'block', 'type': 'callout', 'callout': {'icon': {'emoji': '📊'}, 'rich_text': [
   t(f'Total applications: {sent}', bold=True), t(f' since {since} ({total} jobs tracked, {not_sent} not applied)'), t(f' · {open_n} open · {f["Interview"]} reached interview · {f["Offer"]} offer · {rej} rejected ({rej/max(sent, 1):.0%})' + (f' · median {med} days to a first decision' if med is not None else '') + f'\nUpdated {today} by the job-autopilot sync.')]}},
]
if DASH_URL:
    children.append({'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': [t('Interactive version with hover details, open pipeline table and search: '), {'type': 'text', 'text': {'content': 'Job Search Dashboard', 'link': {'url': DASH_URL}}}]}})
# charts first: pie | flow side by side, weekly on its own (PNGs from tools/charts_png.py)
def image(name, caption):
    return {'object': 'block', 'type': 'image', 'image': {'type': 'file_upload', 'file_upload': {'id': upload(os.path.join(OUTDIR, name))}, 'caption': [t(caption)]}}
def column(*kids): return {'object': 'block', 'type': 'column', 'column': {'children': list(kids)}}
children += [
 {'object': 'block', 'type': 'column_list', 'column_list': {'children': [
   column(image('pie.png', f'Where every application stands: {sent} applications sent, {not_sent} jobs tracked but not applied. Applied = platform receipt only, Confirmed = company acknowledged receipt.')),
   column(image('flow.png', 'How applications flow between stages. Band width = number of applications.'))]}},
 {'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [t('Applications per week')]}},
 image('weekly.png', 'Applications per ISO week, by platform.'),
]
# strategy review table (lower part): only once applications carry a mode or a posting date
def table(head, body):
    row = lambda cells: {'type': 'table_row', 'table_row': {'cells': [[t(str(c))] for c in cells]}}
    return {'object': 'block', 'type': 'table', 'table': {'table_width': len(head), 'has_column_header': True, 'has_row_header': False,
            'children': [row(head)] + [row(b) for b in body]}}
known = [(f'Mode: {k}', v) for k, v in d.get('by_mode', {}).items() if k != 'unknown'] + \
        [(f'Posting age: {k}', v) for k, v in d.get('by_age', {}).items() if k != 'unknown']
if known:
    children += [{'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [t('Which applications get interviews')]}},
                 table(['Group', 'Applied', 'Interview', 'Rate'], [[k, v['applied'], v['interview'], f"{v['rate']:.0%}"] for k, v in known]),
                 {'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': [t('Tailored vs template and how old the posting was when you applied (standards/de/apply-strategy.md). Shift effort to the groups with the higher rate.', italic=True)]}}]
if db_i is not None and anchor:   # a heading right above the database, which stays at the bottom
    children.append({'object': 'block', 'type': 'heading_1', 'heading_1': {'rich_text': [t('Database')]}})
r = requests.patch(f'https://api.notion.com/v1/blocks/{PAGE}/children', headers=HJ, json={'children': children, **({'after': anchor} if anchor else {})})
print('removed', removed, 'old blocks; appended', len(children), '->', r.status_code, r.text[:200] if r.status_code != 200 else 'ok')
