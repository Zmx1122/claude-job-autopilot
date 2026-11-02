"""Record one job in Notion and data/applied.csv (create or update, keyed by job URL, then company+title).

usage: python3 tools/log_application.py --title "AI Engineer (m/w/d)" --company "ACME AG" --platform LinkedIn \
          --status Applied --url https://... [--city Munich] [--salary "80-95k"] [--notes "..."] [--source auto]
status: Seen | Shortlisted | Applied | Skipped (later stages come from the mail sync)
Use it right after every submit, and for every job you shortlist or skip during a scan, so tomorrow's scan dedupes against it.
"""
import argparse, csv, os
from datetime import date
from common import DATA, load_env, notion_rows, notion_call, rt, same_company, title_sim

ap = argparse.ArgumentParser()
for k in ('title', 'company', 'platform', 'status', 'url', 'city', 'salary', 'notes', 'source', 'date'):
    ap.add_argument('--' + k, default='')
ap.add_argument('--dry-run', action='store_true')
a = ap.parse_args()
a.status = a.status or 'Applied'; a.source = a.source or 'auto'; a.platform = a.platform or 'Other'; a.date = a.date or str(date.today())
env = load_env()
rows = notion_rows(env)
hit = next((r for r in rows if a.url and r['url'] and r['url'].split('?')[0] == a.url.split('?')[0]), None) or \
      next((r for r in rows if same_company(a.company, r['company']) and (title_sim(a.title, r['title']) or 0) >= 0.8), None)
props = {'Title': {'title': [{'text': {'content': a.title}}]}, 'Company': rt(a.company), 'Platform': {'select': {'name': a.platform}},
         'Status': {'select': {'name': a.status}}, 'Source': {'select': {'name': a.source}}}
if a.url: props['URL'] = {'url': a.url}
if a.city: props['City'] = rt(a.city)
if a.salary: props['Salary Range'] = rt(a.salary)
if a.status in ('Applied',): props['Applied On'] = {'date': {'start': a.date}}
if a.notes: props['Notes'] = rt(((hit or {}).get('notes', '') + ' | ' if hit and hit.get('notes') else '') + a.notes)
if a.dry_run:
    raise SystemExit(f"dry run: would {'update' if hit else 'create'} {a.company} · {a.title} → {a.status}" + (f" (matches existing row: {hit['title']})" if hit else ''))
if hit:
    r = notion_call('PATCH', f"https://api.notion.com/v1/pages/{hit['id']}", env, json={'properties': props}); what = 'updated'
else:
    props['First Seen'] = {'date': {'start': a.date}}
    r = notion_call('POST', 'https://api.notion.com/v1/pages', env, json={'parent': {'database_id': env['NOTION_DATABASE_ID']}, 'properties': props}); what = 'created'
if r.status_code != 200:
    raise SystemExit(f'Notion {r.status_code}: {r.text[:300]}')
path = os.path.join(DATA, 'applied.csv'); new = not os.path.exists(path)
with open(path, 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(['date', 'platform', 'company', 'title', 'url', 'status', 'notes'])
    w.writerow([a.date, a.platform, a.company, a.title, a.url, a.status.lower(), a.notes])
print(f'{what} Notion row ({a.status}) and logged to data/applied.csv: {a.company} · {a.title}')
