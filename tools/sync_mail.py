"""Daily mail sync: apply classified emails to the existing Notion rows.

usage: python3 tools/sync_mail.py [--apply] [--rebuild] [--mail-dir data/mail]
reads  data/mail/dump.json + data/mail/classified_*.json (or those in --mail-dir)
writes data/mail/sync_report.md (always) and, with --apply, updates Notion and labels the emails in Gmail.
Without --apply it is a dry run: read the report, then run again with --apply.

Matching order for every email: same Gmail thread as a known row → same company (+ similar title) → same platform + title
for platform receipts without a company. Unmatched submissions become new rows with Source=manual and are listed under
"Please confirm" so the user can say whether they applied by hand.

Stage (detailed progress, tools/stage.py): every matched email moves the row's Stage forward (一面邀请 → 已参加一面 → 二面邀请 …,
参加一面后被拒, 一面邀请后撤回 …); Status is derived from it. An interview whose Interview Date has passed becomes 已参加N面.
Rows never applied to get Applied On = "放弃投递".

--rebuild: recompute Stage, Status, Events and Last Email of every row from a full mailbox dump (e.g. gmail_dump.py --since
2026/06/20 into data/mail/rebuild/ and classify it there). Rows are never created, emails are not labeled; statuses the user
set by hand (Withdrawn, Skipped, Offer, Rejected without a mail) are kept and turned into the matching stage. The report lists
every status change for checking before --apply.
"""
import glob, json, os, re, sys, subprocess
from datetime import timezone, date
from email.utils import parsedate_to_datetime
from common import (DATA, ROOT, load_env, notion_rows, notion_call, rt, gmail_link, same_company, title_sim, title_tokens, load_json, label_name,
                    db_props, applied_value, iso_day, NOT_APPLIED)
from stage import next_stage, from_status, status_of, held, withdrawn_stage, parse, rname

APPLY = '--apply' in sys.argv
REBUILD = '--rebuild' in sys.argv
MAIL = sys.argv[sys.argv.index('--mail-dir') + 1] if '--mail-dir' in sys.argv else os.path.join(DATA, 'mail')
dump = {r['msgid']: r for r in json.load(open(os.path.join(MAIL, 'dump.json')))}
cls = []
for f in sorted(glob.glob(os.path.join(MAIL, 'classified_*.json'))):
    cls += json.load(open(f))
env = load_env()
rows = notion_rows(env)
STAGED = 'Stage' in db_props(env)
TODAY = date.today()
for row in rows:
    row['_stage'] = '' if REBUILD else (row['stage'] or from_status(row['status']))
    row['_idate'] = '' if REBUILD else row['interview_date']
    row['_old'] = dict(stage=row['stage'], status=row['status'], events=row['events'])
    if REBUILD: row['events'] = ''; row['last_email'] = ''
OV = load_json(os.path.join(ROOT, 'config', 'overrides.json'), None) or {}
ALIAS = {k.lower(): v for k, v in (OV.get('aliases') or {}).items()}

STATUS = {'interview': 'Interview', 'rejection': 'Rejected', 'offer': 'Offer', 'withdrawn': 'Withdrawn', 'delivery_failed': 'Skipped'}
RANK = {'Seen': 0, 'Shortlisted': 1, 'Applied': 2, 'Confirmed': 3, 'Interview': 4, 'Offer': 5}
TERMINAL = ('Rejected', 'Withdrawn', 'Skipped')
IGNORE = {'recruiter_outreach', 'account_admin', 'job_alert', 'other', 'viewed', 'incomplete_reminder'}
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
    if c.get('category') == 'own_message' and c.get('step') != 'withdraw': continue   # the user's own mail matters only when it withdraws
    e = {k: (str(c.get(k) or '')).strip() for k in ('category', 'company', 'title', 'platform', 'job_url', 'job_id', 'city', 'salary', 'note',
                                                    'step', 'interview_date', 'after_interview')}
    e['round'] = c.get('round') if isinstance(c.get('round'), int) else None
    e['interview_date'] = iso_day(e['interview_date'])
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
    d = iso_day(r.get('applied')) or iso_day(r.get('first_seen'))
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

def is_open(r):
    """Rebuild replays from scratch: a row is open until the replayed mail ends it (the current status may come from a mismatch)."""
    if REBUILD and r.get('id'): return status_of(r['_stage']) not in TERMINAL
    return r['status'] not in TERMINAL

def match(e):
    t = by_thread.get(f"{int(e['thrid']):x}") if e['thrid'] else None
    if t: return t, 'thread'
    pool = [r for r in rows + created if e['company'] and same_company(e['company'], r['company'])]
    if pool:
        live = [r for r in pool if is_open(r)] or pool
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
        cand = [r for r in rows + created if r['platform'] == e['platform'] and is_open(r) and near(r, e, 3)
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
    if not e['labeled'] and not REBUILD: to_label.append(e['msgid'])
    if row is None and REBUILD:
        confirm.append(dict(applied=str(e['day']), company=e['company'], title=f"{e['title']} ({e['category']}, not written: rebuild)", status=''))
        continue
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
            new['stage'], new['interview_date'] = next_stage('', e)
            new['status'] = status_of(new['stage']) or new['status']
            created.append(new)
            if e['thrid']: by_thread[f"{int(e['thrid']):x}"] = new
            confirm.append(new)
        continue
    last = max(e['day'], date.fromisoformat(row['last_email'])) if row['last_email'] else e['day']
    upd = {'last_email': str(last)}
    st0 = row['_stage']; row['_stage'], row['_idate'] = next_stage(st0, e, row['_idate'])
    if row['_stage'] != st0: ev_txt += f" → {row['_stage']}"
    elif e['category'] == 'interview' and e['step']: ev_txt += f" ({e['step']})"
    if ev_txt not in row['events']: upd['events'] = (row['events'] + '; ' if row['events'] else '') + ev_txt
    if e['note'] and e['note'] not in row['notes'] and not REBUILD: upd['notes'] = (row['notes'] + ' | ' if row['notes'] else '') + f"{e['day']}: {e['note']}"
    if not row['evidence'] and e['category'] in ('application_sent', 'ats_confirmation'):
        upd['evidence'] = link
        if e['thrid']: upd['thread'] = gmail_link(e['thrid'])
    for k in ('company', 'city', 'salary', 'job_id'):
        if not row[k] and e[k]: upd[k] = e[k]
    if not row['url'] and e['job_url']: upd['url'] = e['job_url']
    if e['category'] in ('application_sent', 'ats_confirmation') and not row['applied']:
        upd['applied'] = str(e['day'])
    if how != 'thread' and how != 'company+title':
        unsure.append((row, e, how))
    if e['thrid']: by_thread.setdefault(f"{int(e['thrid']):x}", row)
    change(row, **upd)

# ---------- stage and status per row ----------
RANKS = {'Shortlisted': 1, 'Skipped': 1, 'Applied': 2, 'Confirmed': 3, 'Interview': 4, 'Offer': 5, 'Rejected': 6, 'Withdrawn': 6}
status_checks = []
def reconcile(row, s):
    """Rebuild: keep what the user set by hand that the mailbox cannot know."""
    cur, new = row['status'], status_of(s)
    if cur == new: return s
    if cur == 'Withdrawn' and new not in ('Rejected', 'Offer'): return withdrawn_stage(s or '已投递')
    if cur == 'Skipped' and not row['applied']: return '放弃投递'
    if cur == 'Offer': return '收到Offer'
    if cur == 'Rejected' and new not in ('Withdrawn', 'Offer'):
        n = parse(s)['round']; return f"参加{rname(n)}后被拒" if n else ('测评后被拒' if parse(s)['phase'] == 'assess' else '简历被拒')
    if cur == 'Interview' and RANKS.get(new, 0) < RANKS['Interview'] and parse(s)['phase'] != 'docs': return '一面邀请'   # invitation by phone / LinkedIn
    return s
for row in rows:
    s = row['_stage'] or from_status(row['status'])
    if REBUILD: s = reconcile(row, s)
    s = held(s, row['_idate'], TODAY)
    upd = {}
    if STAGED and s and s != row['stage']: upd['stage'] = s
    if STAGED and row['_idate'] != row['interview_date']: upd['interview_date'] = row['_idate']
    new_status = status_of(s) or row['status']
    if new_status != row['status']:
        upd['status'] = new_status
        if REBUILD: status_checks.append((row, row['status'], new_status, s))
    if (new_status == 'Skipped' or s == '放弃投递') and not row['applied_text']: upd['applied'] = NOT_APPLIED
    if upd: change(row, **upd)

# ---------- report ----------
lines = [f'# Mail sync {date.today()}', '', f'{len(events)} relevant emails, {len(changes)} rows updated, {len(created)} new rows, {len(to_label)} emails to label.', '']
if changes:
    lines += ['## Updated rows', '', '| Company | Title | Change |', '|---|---|---|']
    for ch in changes.values():
        r = ch['row']; s = ', '.join(f'{k}→{v}' for k, v in ch['set'].items() if k in ('status', 'evidence')) or 'last email / events'
        lines.append(f"| {r['company']} | {r['title'][:60]} | {s} |")
    lines.append('')
if STAGED:
    st = [(ch['row']) for ch in changes.values() if 'stage' in ch['set']]
    if st:
        lines += [f'## Stage changes ({len(st)})', '', '| Company | Title | Stage before | Stage now | Status |', '|---|---|---|---|---|']
        lines += [f"| {r['company'] or '?'} | {r['title'][:50]} | {r['_old']['stage'] or '–'} | {r['stage']} | {r['status']} |"
                  for r in sorted(st, key=lambda r: r['stage'])]
        lines.append('')
if status_checks:
    lines += [f'## Status changes from the rebuild ({len(status_checks)}) — check', '', '| Company | Title | Status before | now | Stage |', '|---|---|---|---|---|']
    lines += [f"| {r['company'] or '?'} | {r['title'][:50]} | {a} | {b} | {s} |" for r, a, b, s in status_checks]
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
json.dump([dict(company=ch['row']['company'], title=ch['row']['title'], set={k: ch['row'][k] for k in ch['set']}, before=ch['row'].get('_old'))
           for ch in changes.values()], open(os.path.join(MAIL, 'preview.json'), 'w'), ensure_ascii=False, indent=1)
print('\n'.join(lines))

if not APPLY:
    print('\n(dry run; nothing written. Re-run with --apply.)'); sys.exit(0)

def props(r, keys):
    P = {'title': lambda v: {'title': [{'text': {'content': v or '(title unknown)'}}]}, 'company': rt, 'city': rt, 'salary': rt, 'job_id': rt, 'events': rt, 'notes': rt,
         'status': lambda v: {'select': {'name': v}}, 'platform': lambda v: {'select': {'name': v}}, 'source': lambda v: {'select': {'name': v}},
         'applied': lambda v: applied_value(env, v), 'stage': lambda v: {'select': {'name': v}} if v else {'select': None},
         'interview_date': lambda v: {'date': {'start': v}} if v else {'date': None}, 'last_email': lambda v: {'date': {'start': v}} if v else {'date': None},
         'url': lambda v: {'url': v or None}, 'evidence': lambda v: {'url': v or None}, 'thread': lambda v: {'url': v or None}}
    N = {'title': 'Title', 'company': 'Company', 'city': 'City', 'salary': 'Salary Range', 'job_id': 'Job ID', 'events': 'Events', 'notes': 'Notes',
         'status': 'Status', 'platform': 'Platform', 'source': 'Source', 'applied': 'Applied On', 'last_email': 'Last Email', 'url': 'URL',
         'evidence': 'Email Evidence', 'thread': 'Email Thread', 'stage': 'Stage', 'interview_date': 'Interview Date'}
    return {N[k]: P[k](r[k]) for k in keys if k in N}
for ch in changes.values():
    if ch['row'].get('id'):
        r = notion_call('PATCH', f"https://api.notion.com/v1/pages/{ch['row']['id']}", env, json={'properties': props(ch['row'], ch['set'].keys())})
        if r.status_code != 200: print('ERR update', r.status_code, r.text[:200])
for c in created:
    keys = [k for k in c if k not in ('id',) and not (k in ('stage', 'interview_date') and not STAGED)]
    p = props(c, keys); p['First Seen'] = {'date': {'start': c['applied']}}
    r = notion_call('POST', 'https://api.notion.com/v1/pages', env, json={'parent': {'database_id': env['NOTION_DATABASE_ID']}, 'properties': p})
    if r.status_code != 200: print('ERR create', r.status_code, r.text[:200])
if to_label:
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'label_mail.py'), os.path.join(MAIL, 'to_label.json')])
print(f'applied: {len(changes)} updates, {len(created)} new rows, label "{label_name(env)}" added to {len(to_label)} emails')
