"""Backfill upload: create or update tracker rows (Notion or local CSV) from apps.json (output of merge.py). Key: Email Evidence URL.

usage: python3 tools/notion_upsert.py data/mail/apps.json
"""
import json, sys, time
from common import *   # applied_value: text or date column; notion_rows / notion_call serve both backends
env = load_env(); LOCAL = is_local(env)
DB = env.get('NOTION_DATABASE_ID', '')
def existing(): return {r['evidence']: r['id'] for r in notion_rows(env) if r['evidence']}
def props(a):
    p = {'Title': {'title': [{'text': {'content': a['title'] or '(title unknown)'}}]}, 'Company': rt(a['company']), 'City': rt(a.get('city','')), 'Salary Range': rt(a.get('salary','')),
         'First Seen': {'date': {'start': a['applied']}}, 'Applied On': applied_value(env, a['applied']), 'Last Email': {'date': {'start': a['last_email']}},
         'Platform': {'select': {'name': a['platform']}}, 'Status': {'select': {'name': a['status']}}, 'Source': {'select': {'name': a.get('source','manual')}},
         'Email Evidence': {'url': a['evidence']}, 'Job ID': rt(a.get('job_id','')), 'Events': rt(a.get('events_text','')), 'Notes': rt(' | '.join(a.get('notes', [])))}
    if a.get('job_url'): p['URL'] = {'url': a['job_url']}
    if a.get('thread'): p['Email Thread'] = {'url': a['thread']}
    return p
apps = json.load(open(sys.argv[1])); have = existing(); created = updated = 0
for a in apps:
    pid = have.get(a['evidence'])
    if pid: r = notion_call('PATCH', f'https://api.notion.com/v1/pages/{pid}', env, json={'properties': props(a)}); updated += 1
    else: r = notion_call('POST', 'https://api.notion.com/v1/pages', env, json={'parent': {'database_id': DB}, 'properties': props(a)}); created += 1
    if r.status_code != 200: print('ERR', r.status_code, r.text[:200], a['company'], a['title'])
    if not LOCAL: time.sleep(0.34)
print(f'created {created}, updated {updated}')
