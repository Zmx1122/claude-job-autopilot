"""Rebuild the Dashboard section on the Notion Job Search page: headline numbers (total applications first), link to the interactive
dashboard, and the chart images from tools/charts_png.py (run dashboard_data.py and charts_png.py first). No Mermaid code blocks."""
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
# 1. remove the old dashboard section (everything from the marker heading up to the next heading_1 or the database)
blocks, cursor = [], None
while True:
    r = requests.get(f'https://api.notion.com/v1/blocks/{PAGE}/children', headers=H, params={'page_size': 100, **({'start_cursor': cursor} if cursor else {})}).json()
    blocks += r['results']
    if not r.get('has_more'): break
    cursor = r['next_cursor']
inside = False; removed = 0
for b in blocks:
    if b['type'] == 'heading_1' and ''.join(x['plain_text'] for x in b['heading_1']['rich_text']) == MARK: inside = True
    elif b['type'] in ('heading_1', 'child_database'): inside = False
    if inside: requests.delete(f"https://api.notion.com/v1/blocks/{b['id']}", headers=H); removed += 1
# 2. build the new section
s = d['by_status']; f = d['funnel']; total = d['total']; open_n = len(d['open_rows']); rej = s.get('Rejected', 0)
not_sent = s.get('Skipped', 0) + s.get('Shortlisted', 0) + s.get('Seen', 0)   # 放弃投递 / 待定: tracked, never sent
sent = total - not_sent
med = d['response_days'][len(d['response_days']) // 2] if d['response_days'] else None
if not d['total']:
    raise SystemExit('No applications in the database yet; the dashboard is built after the first rows exist.')
today = _dt.date.today().isoformat()
since = min((r['applied'] for r in d['rows'] if r.get('applied')), default=today)
children = [
 {'object': 'block', 'type': 'heading_1', 'heading_1': {'rich_text': [t(MARK)]}},
 {'object': 'block', 'type': 'callout', 'callout': {'icon': {'emoji': '📊'}, 'rich_text': [
   t(f'Total applications: {sent}', bold=True), t(f' since {since} ({total} jobs tracked, {not_sent} not applied)'), t(f' · {open_n} open · {f["Interview"]} reached interview · {f["Offer"]} offer · {rej} rejected ({rej/max(sent, 1):.0%})' + (f' · median {med} days to a first decision' if med is not None else '') + f'\nUpdated {today} by the job-autopilot sync.')]}},
]
if DASH_URL:
    children.append({'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': [t('Interactive version with hover details, open pipeline table and search: '), {'type': 'text', 'text': {'content': 'Job Search Dashboard', 'link': {'url': DASH_URL}}}]}})
# strategy review table: only once applications carry a mode or a posting date
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
# Charts: only the PNGs drawn by tools/charts_png.py (Mermaid code blocks showed their source code above every chart)
children += [{'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [t(f'Charts · total applications: {sent}')]}}]
for name, caption in (('pie.png', f'Where every application stands: {sent} applications sent, {not_sent} jobs tracked but not applied ({total} rows). Applied = platform receipt only, Confirmed = company acknowledged receipt.'),
                      ('flow.png', 'How applications flow between stages. Band width = number of applications.'),
                      ('weekly.png', 'Applications per ISO week, by platform.')):
    fid = upload(os.path.join(OUTDIR, name))
    children.append({'object': 'block', 'type': 'image', 'image': {'type': 'file_upload', 'file_upload': {'id': fid}, 'caption': [t(caption)]}})
r = requests.patch(f'https://api.notion.com/v1/blocks/{PAGE}/children', headers=HJ, json={'children': children})
print('removed', removed, 'old blocks; appended', len(children), '->', r.status_code, r.text[:200] if r.status_code != 200 else 'ok')
