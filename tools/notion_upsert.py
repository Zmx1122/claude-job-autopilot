"""Backfill upload: create or update Notion rows from apps.json (output of merge.py). Key: Email Evidence URL.

usage: python3 tools/notion_upsert.py data/mail/apps.json
"""
import json, sys, time, requests
from common import *   # applied_value: text or date column
env = load_env(); H = {'Authorization': f"Bearer {env['NOTION_TOKEN']}", 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'}
DB = env['NOTION_DATABASE_ID']
def rt(s): return {'rich_text': [{'text': {'content': (s or '')[:1900]}}]}
def existing():
    rows, cursor = {}, None
    while True:
        body = {'page_size': 100, **({'start_cursor': cursor} if cursor else {})}
        d = requests.post(f'https://api.notion.com/v1/databases/{DB}/query', headers=H, json=body).json()
        for p in d.get('results', []):
            ev = (p['properties'].get('Email Evidence') or {}).get('url')
            if ev: rows[ev] = p['id']
        if not d.get('has_more'): return rows
        cursor = d['next_cursor']
def props(a):
    p = {'Title': {'title': [{'text': {'content': a['title'] or '(title unknown)'}}]}, 'Company': rt(a['company']), 'City': rt(a.get('city','')), 'Salary Range': rt(a.get('salary','')),
         'First Seen': {'date': {'start': a['applied']}}, **applied_props(env, a['applied']), 'Last Email': {'date': {'start': a['last_email']}},
         'Platform': {'select': {'name': a['platform']}}, 'Status': {'select': {'name': a['status']}}, 'Source': {'select': {'name': a.get('source','manual')}},
         'Email Evidence': {'url': a['evidence']}, 'Job ID': rt(a.get('job_id','')), 'Events': rt(a.get('events_text','')), 'Notes': rt(' | '.join(a.get('notes', [])))}
    if a.get('job_url'): p['URL'] = {'url': a['job_url']}
    if a.get('thread'): p['Email Thread'] = {'url': a['thread']}
    return p
apps = json.load(open(sys.argv[1])); have = existing(); created = updated = 0
for a in apps:
    pid = have.get(a['evidence'])
    if pid: r = requests.patch(f'https://api.notion.com/v1/pages/{pid}', headers=H, json={'properties': props(a)}); updated += 1
    else: r = requests.post('https://api.notion.com/v1/pages', headers=H, json={'parent': {'database_id': DB}, 'properties': props(a)}); created += 1
    if r.status_code != 200: print('ERR', r.status_code, r.text[:200], a['company'], a['title'])
    time.sleep(0.34)
print(f'created {created}, updated {updated}')
