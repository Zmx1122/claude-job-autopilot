"""Rebuild the Dashboard section on the Notion Job Search page: headline numbers, link to the interactive dashboard, chart images."""
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
med = d['response_days'][len(d['response_days']) // 2] if d['response_days'] else None
if not d['total']:
    raise SystemExit('No applications in the database yet; the dashboard is built after the first rows exist.')
today = _dt.date.today().isoformat()
since = min((r['applied'] for r in d['rows'] if r.get('applied')), default=today)
children = [
 {'object': 'block', 'type': 'heading_1', 'heading_1': {'rich_text': [t(MARK)]}},
 {'object': 'block', 'type': 'callout', 'callout': {'icon': {'emoji': '📊'}, 'rich_text': [
   t(f'{total} applications since {since}', bold=True), t(f' · {open_n} open · {f["Interview"]} reached interview · {f["Offer"]} offer · {rej} rejected ({rej/total:.0%})' + (f' · median {med} days to a first decision' if med is not None else '') + f'\nUpdated {today} by the job-autopilot sync.')]}},
]
if DASH_URL:
    children.append({'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': [t('Interactive version with hover details, open pipeline table and search: '), {'type': 'text', 'text': {'content': 'Job Search Dashboard', 'link': {'url': DASH_URL}}}]}})
# Mermaid blocks render natively in Notion (pie, sankey-beta, xychart-beta)
order = ['Applied', 'Confirmed', 'Interview', 'Offer', 'Rejected', 'Withdrawn', 'Skipped']
pie = 'pie showData\n    title Where every application stands\n' + ''.join(f'    "{k}" : {s[k]}\n' for k in order if s.get(k))
wait = {'Applied': 'No reply yet', 'Confirmed': 'Waiting after confirmation', 'Interview': 'Interview pending'}
def sk_name(src, tgt):
    if tgt in ('Confirmed', 'Interview', 'Offer'): return tgt
    if tgt.startswith('Waiting at '): return wait[tgt[11:]]
    return f'{tgt} after {src.lower()}'
sankey = 'sankey-beta\n\n' + ''.join(f"{l['source']},{sk_name(l['source'], l['target'])},{l['value']}\n" for l in d['sankey'])
wk = d['weekly']; plats = [p for p in ['LinkedIn', 'StepStone', 'Indeed', 'Xing', 'Other'] if any(w.get(p) for w in wk)]
xy = 'xychart-beta\n    title "Applications per week"\n    x-axis [' + ', '.join('"W' + w['week'][6:] + '"' for w in wk) + ']\n    y-axis "Applications" 0 --> ' + str(max(w['total'] for w in wk) + 2) + '\n    bar [' + ', '.join(str(w['total']) for w in wk) + ']\n'
def code(src): return {'object': 'block', 'type': 'code', 'code': {'language': 'mermaid', 'rich_text': [t(src)]}}
children += [
 {'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [t('Stage of every application')]}}, code(pie),
 {'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [t('Flow between stages')]}}, code(sankey),
 {'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [t('Applications per week')]}}, code(xy),
 {'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [t('Charts as images')]}},
]
for name, caption in (('pie.png', 'Where every application stands. Applied = platform receipt only, Confirmed = company acknowledged receipt.'),
                      ('flow.png', 'How applications flow between stages. Band width = number of applications.'),
                      ('weekly.png', 'Applications per ISO week, by platform.')):
    fid = upload(os.path.join(OUTDIR, name))
    children.append({'object': 'block', 'type': 'image', 'image': {'type': 'file_upload', 'file_upload': {'id': fid}, 'caption': [t(caption)]}})
r = requests.patch(f'https://api.notion.com/v1/blocks/{PAGE}/children', headers=HJ, json={'children': children})
print('removed', removed, 'old blocks; appended', len(children), '->', r.status_code, r.text[:200] if r.status_code != 200 else 'ok')
