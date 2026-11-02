"""Backfill: merge classified emails into application records (one record per application).

usage: python3 tools/merge.py data/mail/dump.json data/mail/classified_*.json -o data/mail/apps.json
Use this once for the initial backfill (e.g. everything since your search started). For the daily run use sync_mail.py,
which matches new emails against the rows already in Notion.
Company aliases / manual fixes go in config/overrides.json (see config/overrides.example.json).
"""
import json, sys, re, os
from email.utils import parsedate_to_datetime
from datetime import timezone
from common import *
args = sys.argv[1:]; out = args[args.index('-o')+1]; args.remove('-o'); args.remove(out)
OV = load_json(os.path.join(ROOT, 'config', 'overrides.json'), None) or {'aliases': {}, 'not_same': [], 'email_fixes': []}
ALIASES = {norm_company(k): v for k, v in OV.get('aliases', {}).items()}
def canon(c):
    c = (c or '').strip(); n = norm_company(c)
    return ALIASES.get(n, c)
def same(a, b):
    na, nb = norm_company(canon(a)), norm_company(canon(b))
    if not na or not nb: return False
    if [na, nb] in OV.get('not_same', []) or [nb, na] in OV.get('not_same', []): return False
    if na == nb: return True
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= 4 and short in long_: return True
    A = {t for t in na.split() if len(t) >= 3}; B = {t for t in nb.split() if len(t) >= 3}
    return bool(A and B) and (A <= B or B <= A)
dump = json.load(open(args[0])); byid = {r['msgid']: r for r in dump if r['msgid']}
cls = []
for f in args[1:]: cls += json.load(open(f))
def ts(r):
    d = parsedate_to_datetime(r['date']); return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
events = []
for c in cls:
    r = byid.get(c['msgid'])
    if not r: continue
    e = dict(c); e['t'] = ts(r); e['date'] = e['t'].strftime('%Y-%m-%d'); e['subject'] = re.sub(r'\s+', ' ', r['subject']); e['frm'] = r['frm']; e['thrid'] = r['thrid']
    e['link'] = gmail_link(c['msgid']); e['labeled'] = r.get('set') == 'labeled'
    for k in ('company','title','platform','job_url','job_id','city','salary','note'): e[k] = (e.get(k) or '').strip()
    for fx in OV.get('email_fixes', []):
        if e['date'] == fx['date'] and fx['subject'] in e['subject'] and fx['from'].lower() in e['frm'].lower():
            for k in ('company','title'):
                if fx.get(k): e[k] = fx[k]
            if fx.get('note'): e['note'] = (e['note'] + ' ' + fx['note']).strip()
    e['company'] = canon(e['company'])
    events.append(e)
PRIO = {'application_sent': 0, 'ats_confirmation': 1}
events.sort(key=lambda e: (e['date'], PRIO.get(e['category'], 2), e['t']))
PLAT = ('LinkedIn','StepStone','Indeed','Xing')
STATUS = {'interview':'Interview','rejection':'Rejected','offer':'Offer','withdrawn':'Withdrawn','delivery_failed':'Skipped'}
TERMINAL = ('Rejected','Withdrawn','Skipped')
apps = []
def new_app(e, note=None):
    a = dict(t=e['t'], applied=e['date'], company=e['company'], title=e['title'], platform=e['platform'] if (e['platform'] in PLAT and e['category']=='application_sent') else 'Other',
             status='Confirmed' if e['category']=='ats_confirmation' else ('Applied' if e['category']=='application_sent' else STATUS.get(e['category'],'Applied')),
             evidence=e['link'], thread=gmail_link(e['thrid']) if e['thrid'] else '', job_url=e['job_url'], job_id=e['job_id'], city=e['city'], salary=e['salary'],
             ats=(e['category']=='ats_confirmation'), source='manual', events=[e], notes=[n for n in (note, e['note']) if n], threads={e['thrid']}, terminal_date=None)
    apps.append(a); return a
def attach(a, e):
    a['events'].append(e); a['threads'].add(e['thrid'])
    for k in ('company','title','job_url','job_id','city','salary'):
        if not a[k] and e[k]: a[k] = e[k]
    if a['platform'] == 'Other' and e['platform'] in PLAT and e['category'] == 'application_sent':
        a['platform'] = e['platform']; a['evidence'] = e['link']; a['applied'] = min(a['applied'], e['date'])
    if e['category'] == 'ats_confirmation':
        a['ats'] = True
        if a['status'] == 'Applied': a['status'] = 'Confirmed'
    if e['category'] in STATUS:
        a['status'] = STATUS[e['category']]
        a['terminal_date'] = e['date'] if a['status'] in TERMINAL else None
    if e['note']: a['notes'].append(f"{e['date']}: {e['note']}")
def tok(t): return title_tokens(t)
def cands(e, back_days, fwd_hours=6):
    out = []
    for a in apps:
        dt = (e['t'] - a['t']).total_seconds()/3600
        if dt < -fwd_hours or dt > back_days*24: continue
        tsim = title_sim(e['title'], a['title']) if e['title'] and a['title'] else None
        exact = bool(e['title'] and a['title'] and tok(e['title']) == tok(a['title']))
        out.append(dict(a=a, cs=same(e['company'], a['company']), tsim=tsim, exact=exact, dt=abs(dt)))
    return out
def best(cc):
    return sorted(cc, key=lambda c: (-(c['exact']), -(c['tsim'] or 0), c['dt']))[0]['a'] if cc else None
unmatched = []
for e in events:
    cat = e['category']
    if cat in ('recruiter_outreach','account_admin','job_alert','other'): continue
    by_thread = [a for a in apps if e['thrid'] in a['threads']]
    if by_thread and cat != 'application_sent':
        attach(by_thread[0], e); continue
    if cat == 'application_sent':
        cc = cands(e, 3, fwd_hours=30)
        dup = [c for c in cc if c['a']['platform'] == e['platform'] and c['cs'] and (c['tsim'] is None or c['tsim'] >= 0.8)]
        if dup: attach(best(dup), e); continue
        ats_only = [c for c in cc if c['a']['platform'] == 'Other' and c['dt'] <= 30 and (c['cs'] or ((not c['a']['company'] or not e['company']) and c['tsim'] is not None and c['tsim'] >= 0.75))]
        if ats_only: attach(best(ats_only), e); continue
        new_app(e); continue
    if cat == 'ats_confirmation':
        cc = cands(e, 45)
        byc = [c for c in cc if c['cs'] and not (c['a']['terminal_date'] and c['a']['terminal_date'] < e['date'])
               and (not c['a']['ats'] and (c['tsim'] is None or c['tsim'] >= 0.3) or c['a']['ats'] and (c['exact'] or (c['tsim'] or 0) >= 0.8 or (c['tsim'] is None and c['dt'] <= 72)))]
        if byc: attach(best(byc), e); continue
        byt = [c for c in cc if not c['cs'] and (not c['a']['company'] or not e['company']) and not c['a']['ats'] and c['tsim'] is not None and c['tsim'] >= 0.75]
        if byt: attach(best(byt), e); continue
        new_app(e); continue
    if cat == 'own_message': continue
    cc = cands(e, 180)
    byc = [c for c in cc if c['cs']]
    live = [c for c in byc if not (c['a']['terminal_date'] and c['a']['terminal_date'] < e['date'])]
    pool = live or byc
    if pool:
        titled = [c for c in pool if c['tsim'] is not None and c['tsim'] >= 0.3]
        attach(best(titled) if titled else best([c for c in pool if c['tsim'] is None] or pool), e); continue
    if cat in ('viewed','incomplete_reminder'): unmatched.append(e); continue
    byt = [c for c in cc if (not c['a']['company'] or not e['company']) and c['tsim'] is not None and c['tsim'] >= 0.75]
    if byt: attach(best(byt), e); continue
    new_app(e, note='no application confirmation found in mailbox')
for a in apps:
    a['last_email'] = max(x['date'] for x in a['events'])
    a['events_text'] = '; '.join(f"{x['date'][5:]} {x['category'].replace('_',' ')}" + (f" via {x['platform']}" if x['platform'] else '') for x in a['events'] if x['category'] != 'own_message')
    a['threads'] = sorted(t for t in a['threads'] if t)
    a['event_msgids'] = [x['msgid'] for x in a['events']]
    a['unlabeled_msgids'] = [x['msgid'] for x in a['events'] if not x['labeled']]
    a.pop('terminal_date', None)
json.dump(apps, open(out,'w'), default=str, ensure_ascii=False, indent=1)
import collections
print('events:', collections.Counter(e['category'] for e in events))
print('apps:', len(apps), collections.Counter(a['status'] for a in apps), 'unmatched:', len(unmatched))
print(f"\n{'#':>3} {'applied':10} {'plat':9} {'status':9} {'company':28} | title | events")
for i, a in enumerate(apps):
    print(f"{i:3d} {a['applied']} {a['platform']:9} {a['status']:9} {a['company'][:28]:28} | {a['title'][:50]:50} | {a['events_text'][:105]}")
if unmatched:
    print('\nunmatched:'); [print(' ', e['date'], e['category'], e['company'], '|', e['subject'][:60]) for e in unmatched]
