"""Record one job in Notion and data/applied.csv (create or update, keyed by job URL, then company+title).

usage: python3 tools/log_application.py --title "AI Engineer (m/w/d)" --company "ACME AG" --platform LinkedIn \
          --status Applied --url https://... [--city Munich] [--salary "80-95k"] [--notes "..."] [--source auto]
          [--mode tailored|template] [--cv Jane-Doe-CV-ACME.pdf] [--cover-letter] [--posted 2026-11-03]
          [--stage 一面邀请] [--interview-date 2026-11-17T17:15:00+01:00]
status: Seen | Shortlisted | Applied | Skipped | Withdrawn (later stages come from the mail sync)
The detailed Stage column follows the status: Applied → 已投递, Skipped → 放弃投递 (and Applied On = "放弃投递" unless the row was
applied before), Withdrawn → the matching withdrawal label (一面邀请后撤回, 一面后撤回, 投递后撤回 …). --stage sets it explicitly.
Use it right after every submit, and for every job you shortlist or skip during a scan, so tomorrow's scan dedupes against it.
"""
import argparse, csv, os
from datetime import date
from common import DATA, load_env, notion_rows, notion_call, rt, same_company, title_sim, url_key, db_props, applied_props, NOT_APPLIED
from stage import from_status, withdrawn_stage, parse, STAGES, status_of

ap = argparse.ArgumentParser()
for k in ('title', 'company', 'platform', 'status', 'url', 'city', 'salary', 'notes', 'source', 'date', 'mode', 'cv', 'posted', 'stage'):
    ap.add_argument('--' + k, default='')
ap.add_argument('--interview-date', dest='interview_date', default='')
ap.add_argument('--cover-letter', action='store_true')
ap.add_argument('--dry-run', action='store_true')
a = ap.parse_args()
status_given = bool(a.status); a.status = a.status or 'Applied'; a.source = a.source or 'auto'; a.platform = a.platform or 'Other'; a.date = a.date or str(date.today())
env = load_env()
rows = notion_rows(env)
hit = next((r for r in rows if a.url and r['url'] and url_key(r['url']) == url_key(a.url)), None)
if not hit:
    # Fall back to company + similar title only when the URLs cannot tell the postings apart (one side has none).
    # Two postings with different URLs are different jobs even if the title differs only by "Senior" (title_sim ignores it):
    # 2026-11-09 "Senior Consultant" overwrote "Consultant" at the same company.
    hit = next((r for r in rows if same_company(a.company, r['company']) and (title_sim(a.title, r['title']) or 0) >= 0.8
                and not (a.url and r['url'] and url_key(r['url']) != url_key(a.url))), None)
props = {'Title': {'title': [{'text': {'content': a.title}}]}, 'Company': rt(a.company), 'Platform': {'select': {'name': a.platform}},
         'Status': {'select': {'name': a.status}}, 'Source': {'select': {'name': a.source}}}
if hit and not status_given:   # e.g. only adding a note after a reply: never move an Interview row back to Applied
    a.status = hit['status']; del props['Status']
    for k in ('Platform', 'Source'): props.pop(k)
if a.url: props['URL'] = {'url': a.url}
if a.city: props['City'] = rt(a.city)
if a.salary: props['Salary Range'] = rt(a.salary)
if a.status in ('Applied',) and (status_given or not hit): props.update(applied_props(env, a.date))
if a.status == 'Skipped' and not (hit and hit.get('applied')): props.update(applied_props(env, NOT_APPLIED))
if 'Stage' in db_props(env) and (status_given or a.stage or not hit):
    cur = (hit or {}).get('stage') or from_status((hit or {}).get('status', ''))
    if a.stage: stage = a.stage
    elif a.status == 'Withdrawn': stage = withdrawn_stage(cur)
    elif a.status == 'Applied': stage = cur if parse(cur)['phase'] not in ('', 'pre', 'skipped', 'failed') else '已投递'
    elif a.status == 'Skipped': stage = cur if parse(cur)['phase'] == 'failed' else '放弃投递'
    elif a.status in ('Shortlisted', 'Seen') and not hit: stage = '待定'
    else: stage = '' if a.status in ('Shortlisted', 'Seen') else from_status(a.status)
    if a.stage and a.stage not in STAGES: raise SystemExit(f'unknown --stage {a.stage}; one of: {" ".join(STAGES)}')
    if stage: props['Stage'] = {'select': {'name': stage}}
    if a.stage: props['Status'] = {'select': {'name': status_of(a.stage)}}; a.status = status_of(a.stage)
if a.mode: props['Mode'] = {'select': {'name': a.mode}}
if a.cv: props['CV Version'] = rt(a.cv)
if a.cover_letter: props['Cover Letter'] = {'checkbox': True}
if a.posted: props['Posted'] = {'date': {'start': a.posted}}
if a.interview_date: props['Interview Date'] = {'date': {'start': a.interview_date}}   # YYYY-MM-DD or YYYY-MM-DDTHH:MM+01:00
if a.notes: props['Notes'] = rt(((hit or {}).get('notes', '') + ' | ' if hit and hit.get('notes') else '') + a.notes)
if a.dry_run:
    print(f"dry run: would {'update' if hit else 'create'} {a.company} · {a.title} → {a.status}" + (f" (matches existing row: {hit['title']})" if hit else '')); raise SystemExit(0)
if hit:
    r = notion_call('PATCH', f"https://api.notion.com/v1/pages/{hit['id']}", env, json={'properties': props}); what = 'updated'
else:
    props['First Seen'] = {'date': {'start': a.date}}
    r = notion_call('POST', 'https://api.notion.com/v1/pages', env, json={'parent': {'database_id': env['NOTION_DATABASE_ID']}, 'properties': props}); what = 'created'
if r.status_code != 200:
    raise SystemExit(f'Notion {r.status_code}: {r.text[:300]}')
path = os.path.join(DATA, 'applied.csv'); new = not os.path.exists(path)
if not new:   # older logs have 7 columns: add mode and cv once
    old = list(csv.reader(open(path)))
    if old and 'mode' not in old[0]:
        with open(path, 'w', newline='') as f:
            csv.writer(f).writerows([old[0] + ['mode', 'cv']] + [r + ['', ''] for r in old[1:]])
with open(path, 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(['date', 'platform', 'company', 'title', 'url', 'status', 'notes', 'mode', 'cv'])
    w.writerow([a.date, a.platform, a.company, a.title, a.url, a.status.lower(), a.notes, a.mode, a.cv])
print(f'{what} Notion row ({a.status}) and logged to data/applied.csv: {a.company} · {a.title}')
