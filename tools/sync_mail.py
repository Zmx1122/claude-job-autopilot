"""Daily mail sync: apply classified emails to the existing Notion rows.

usage: python3 tools/sync_mail.py [--apply]
reads  data/mail/dump.json + data/mail/classified_*.json
writes data/mail/sync_report.md (always) and, with --apply, updates Notion and labels the emails in Gmail.
Without --apply it is a dry run: read the report, then run again with --apply.

Matching order for every email: same Gmail thread as a known row → same company (+ similar title) → same platform + title
for platform receipts without a company. Unmatched submissions become new rows with Source=manual and are listed under
"Please confirm" so the user can say whether they applied by hand.
"""
import glob, json, os, re, sys, subprocess
from datetime import timezone, date
from email.utils import parsedate_to_datetime
from common import (DATA, ROOT, load_env, notion_rows, notion_call, rt, gmail_link, same_company, title_sim, title_tokens, load_json, label_name)

APPLY = '--apply' in sys.argv
MAIL = os.path.join(DATA, 'mail')
dump = {r['msgid']: r for r in json.load(open(os.path.join(MAIL, 'dump.json')))}
cls = []
for f in sorted(glob.glob(os.path.join(MAIL, 'classified_*.json'))):
    cls += json.load(open(f))
env = load_env()
rows = notion_rows(env)
OV = load_json(os.path.join(ROOT, 'config', 'overrides.json'), None) or {}
ALIAS = {k.lower(): v for k, v in (OV.get('aliases') or {}).items()}

STATUS = {'interview': 'Interview', 'rejection': 'Rejected', 'offer': 'Offer', 'withdrawn': 'Withdrawn', 'delivery_failed': 'Skipped'}
RANK = {'Seen': 0, 'Shortlisted': 1, 'Applied': 2, 'Confirmed': 3, 'Interview': 4, 'Offer': 5}
TERMINAL = ('Rejected', 'Withdrawn', 'Skipped')
IGNORE = {'recruiter_outreach', 'account_admin', 'job_alert', 'other', 'own_message', 'viewed', 'incomplete_reminder'}
PLAT = ('LinkedIn', 'StepStone', 'Indeed', 'Xing')

def hexid(link): return (link or '').rsplit('/', 1)[-1].lower()
def when(r):
    d = parsedate_to_datetime(r['date']); return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).date()

# Indeed receipts name the employer in the body ("Die folgenden Dokumente wurden an <Firma> übermittelt"), the classifier often leaves it empty.
INDEED_CO = (re.compile(r'wurden an (.{2,80}?) (?:übermittelt|gesendet)', re.I),
             re.compile(r'(?:documents|application) (?:were|was|has been) (?:sent|submitted|delivered) to (.{2,80}?)[.!\n]', re.I))
def indeed_company(r):
    if 'indeed' not in (r.get('frm') or '').lower(): return ''
    for rx in INDEED_CO:
        m = rx.search(r.get('body') or '')
        if m: return re.sub(r'\s+', ' ', m.group(1)).strip(' .,:;')
    return ''

events = []
for c in cls:
    r = dump.get(c.get('msgid'))
    if not r or c.get('category') in IGNORE: continue
    e = {k: (c.get(k) or '').strip() for k in ('category', 'company', 'title', 'platform', 'job_url', 'job_id', 'city', 'salary', 'note')}
    if not e['company'] and c.get('category') in ('application_sent', 'ats_confirmation'): e['company'] = indeed_company(r)
    e['company'] = ALIAS.get(e['company'].lower(), e['company'])
    e.update(msgid=r['msgid'], thrid=r['thrid'], day=when(r), subject=r['subject'], frm=r['frm'], labeled=r.get('set') == 'labeled')
    events.append(e)
events.sort(key=lambda e: (e['day'], 0 if e['category'] == 'application_sent' else 1))

by_thread = {}
for row in rows:
    for link in (row['thread'], row['evidence']):
        if link: by_thread.setdefault(hexid(link), row)

changes, created, confirm, unsure, to_label = {}, [], [], [], []

def day_of(r):
    d = r.get('applied') or r.get('first_seen')
    return date.fromisoformat(d) if d else None

def near(r, e, days):
    d = day_of(r); return d is not None and abs((d - e['day']).days) <= days

def tscore(e, r):
    """1.0 for identical title tokens, else the overlap score scaled below 1."""
    if not e['title'] or not r['title']: return 0
    A, B = title_tokens(e['title']), title_tokens(r['title'])
    return 1.0 if A == B else 0.9 * (title_sim(e['title'], r['title']) or 0)

def pick(cands, e):
    """Best title first, then rows with no email evidence yet, then closest in time. Ambiguous ties → None."""
    if not cands: return None
    def key(r):
        d = day_of(r); return (-round(tscore(e, r), 2), bool(r['evidence']), abs((d - e['day']).days) if d else 999)
    s = sorted(cands, key=key)
    if len(s) > 1 and key(s[0]) == key(s[1]): return None
    return s[0]

def match(e):
    t = by_thread.get(f"{int(e['thrid']):x}") if e['thrid'] else None
    if t: return t, 'thread'
    pool = [r for r in rows + created if e['company'] and same_company(e['company'], r['company'])]
    if pool:
        live = [r for r in pool if r['status'] not in TERMINAL] or pool
        if e['title']:
            scored = [(title_sim(e['title'], r['title']) or 0, r) for r in live]
            top = max(s for s, _ in scored)
            if top >= 0.5:
                r = pick([r for s, r in scored if s == top], e)
                if r: return r, 'company+title'
            # platforms truncate long titles ("Senior Software Engineer" vs "Senior Software Engineer – Autonex ...")
            A = title_tokens(e['title'])
            trunc = [r for r in live if near(r, e, 3) and r['title'] and (A <= title_tokens(r['title']) or title_tokens(r['title']) <= A)]
            r = pick(trunc, e)
            if r: return r, 'company+title'
            if e['category'] == 'application_sent':
                return None, None  # a new application at a known company
        r = pick([r for r in live if near(r, e, 7)], e) or (live[0] if len(live) == 1 else None)
        return (r, 'company') if r else (None, None)
    if e['title'] and e['platform'] in PLAT:
        cand = [r for r in rows + created if r['platform'] == e['platform'] and r['status'] not in TERMINAL and near(r, e, 3)
                and (title_sim(e['title'], r['title']) or 0) >= 0.8]
        r = pick(cand, e)
        if r: return r, 'platform+title'
    return None, None

def change(row, **kw):
    if not row.get('id'):  # a row created earlier in this run: just update the pending dict
        row.update(kw); return
    ch = changes.setdefault(row['id'], {'row': row, 'set': {}, 'log': []})
    ch['set'].update(kw)
    for k, v in kw.items(): row[k] = v

for e in events:
    row, how = match(e)
    ev_txt = f"{e['day'].strftime('%m-%d')} {e['category'].replace('_', ' ')}" + (f" via {e['platform']}" if e['platform'] else '')
    link = gmail_link(e['msgid'])
    if not e['labeled']: to_label.append(e['msgid'])
    if row is None:
        if e['category'] in ('application_sent', 'ats_confirmation') or e['category'] in STATUS:
            new = dict(id=None, title=e['title'] or '(title unknown)', company=e['company'], city=e['city'], salary=e['salary'],
                       platform=e['platform'] if e['category'] == 'application_sent' and e['platform'] in PLAT else 'Other',
                       status='Confirmed' if e['category'] == 'ats_confirmation' else STATUS.get(e['category'], 'Applied'),
                       source='manual', applied=str(e['day']), last_email=str(e['day']), url=e['job_url'], evidence=link,
                       thread=gmail_link(e['thrid']) if e['thrid'] else '', job_id=e['job_id'], events=ev_txt, notes=e['note'])
            if not new['company'] and new['platform'] in PLAT:
                # keep the gap visible instead of leaving a silent blank (a row without a company cannot block duplicates)
                new['notes'] = (new['notes'] + ' | ' if new['notes'] else '') + f"company missing: the {new['platform']} receipt does not name it"
            created.append(new)
            if e['thrid']: by_thread[f"{int(e['thrid']):x}"] = new
            confirm.append(new)
        continue
    last = max(e['day'], date.fromisoformat(row['last_email'])) if row['last_email'] else e['day']
    upd = {'last_email': str(last)}
    if ev_txt not in row['events']: upd['events'] = (row['events'] + '; ' if row['events'] else '') + ev_txt
    if e['note'] and e['note'] not in row['notes']: upd['notes'] = (row['notes'] + ' | ' if row['notes'] else '') + f"{e['day']}: {e['note']}"
    if not row['evidence'] and e['category'] in ('application_sent', 'ats_confirmation'):
        upd['evidence'] = link
        if e['thrid']: upd['thread'] = gmail_link(e['thrid'])
    for k in ('company', 'city', 'salary', 'job_id'):
        if not row[k] and e[k]: upd[k] = e[k]
    if not row['url'] and e['job_url']: upd['url'] = e['job_url']
    cur = row['status']
    if e['category'] == 'application_sent' and RANK.get(cur, 9) < RANK['Applied']:
        upd['status'] = 'Applied'; upd['applied'] = row['applied'] or str(e['day'])
    elif e['category'] == 'ats_confirmation' and RANK.get(cur, 9) < RANK['Confirmed']:
        upd['status'] = 'Confirmed'; upd['applied'] = row['applied'] or str(e['day'])
    elif e['category'] in STATUS:
        new_s = STATUS[e['category']]
        if not (cur == 'Offer' and new_s != 'Offer'): upd['status'] = new_s
    if how != 'thread' and how != 'company+title':
        unsure.append((row, e, how))
    if e['thrid']: by_thread.setdefault(f"{int(e['thrid']):x}", row)
    change(row, **upd)

# ---------- report ----------
lines = [f'# Mail sync {date.today()}', '', f'{len(events)} relevant emails, {len(changes)} rows updated, {len(created)} new rows, {len(to_label)} emails to label.', '']
if changes:
    lines += ['## Updated rows', '', '| Company | Title | Change |', '|---|---|---|']
    for ch in changes.values():
        r = ch['row']; s = ', '.join(f'{k}→{v}' for k, v in ch['set'].items() if k in ('status', 'evidence')) or 'last email / events'
        lines.append(f"| {r['company']} | {r['title'][:60]} | {s} |")
    lines.append('')
if confirm:
    lines += ['## Please confirm', '', 'These emails match no row in Notion. Did you apply to these yourself?', '',
              '| Date | Company | Title | Status from email |', '|---|---|---|---|']
    lines += [f"| {r['applied']} | {r['company'] or '?'} | {r['title'][:60]} | {r['status']} |" for r in confirm]
    lines.append('')
nocomp = [r for r in rows + created if not (r.get('company') or '').strip() and r['status'] in ('Applied', 'Confirmed', 'Interview', 'Offer')]
if nocomp:
    lines += [f'## Rows without a company ({len(nocomp)})', '',
              'A row without a company cannot block a duplicate application. StepStone receipts never name the employer. Complete these from',
              '"Meine Bewerbungen" on the platform (the user can paste the list) or from the company\'s own confirmation email.', '']
    lines += [f"- {r.get('applied') or r.get('first_seen') or '?'} {r['platform']}: {r['title'][:70]}" for r in nocomp[:40]]
    if len(nocomp) > 40: lines.append(f'- ... and {len(nocomp) - 40} more')
    lines.append('')
if unsure:
    lines += ['## Weak matches (check)', '']
    lines += [f"- {e['day']} {e['category']} \"{e['subject'][:70]}\" → {r['company']} / {r['title'][:50]} (matched by {how})" for r, e, how in unsure]
open(os.path.join(MAIL, 'sync_report.md'), 'w').write('\n'.join(lines) + '\n')
json.dump({'to_label': to_label}, open(os.path.join(MAIL, 'to_label.json'), 'w'))
print('\n'.join(lines))

if not APPLY:
    print('\n(dry run; nothing written. Re-run with --apply.)'); sys.exit(0)

def props(r, keys):
    P = {'title': lambda v: {'title': [{'text': {'content': v or '(title unknown)'}}]}, 'company': rt, 'city': rt, 'salary': rt, 'job_id': rt, 'events': rt, 'notes': rt,
         'status': lambda v: {'select': {'name': v}}, 'platform': lambda v: {'select': {'name': v}}, 'source': lambda v: {'select': {'name': v}},
         'applied': lambda v: {'date': {'start': v}} if v else {'date': None}, 'last_email': lambda v: {'date': {'start': v}} if v else {'date': None},
         'url': lambda v: {'url': v or None}, 'evidence': lambda v: {'url': v or None}, 'thread': lambda v: {'url': v or None}}
    N = {'title': 'Title', 'company': 'Company', 'city': 'City', 'salary': 'Salary Range', 'job_id': 'Job ID', 'events': 'Events', 'notes': 'Notes',
         'status': 'Status', 'platform': 'Platform', 'source': 'Source', 'applied': 'Applied On', 'last_email': 'Last Email', 'url': 'URL',
         'evidence': 'Email Evidence', 'thread': 'Email Thread'}
    return {N[k]: P[k](r[k]) for k in keys if k in N}
for ch in changes.values():
    if ch['row'].get('id'):
        r = notion_call('PATCH', f"https://api.notion.com/v1/pages/{ch['row']['id']}", env, json={'properties': props(ch['row'], ch['set'].keys())})
        if r.status_code != 200: print('ERR update', r.status_code, r.text[:200])
for c in created:
    keys = [k for k in c if k not in ('id',)]
    p = props(c, keys); p['First Seen'] = {'date': {'start': c['applied']}}
    r = notion_call('POST', 'https://api.notion.com/v1/pages', env, json={'parent': {'database_id': env['NOTION_DATABASE_ID']}, 'properties': p})
    if r.status_code != 200: print('ERR create', r.status_code, r.text[:200])
if to_label:
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'label_mail.py'), os.path.join(MAIL, 'to_label.json')])
print(f'applied: {len(changes)} updates, {len(created)} new rows, label "{label_name(env)}" added to {len(to_label)} emails')
