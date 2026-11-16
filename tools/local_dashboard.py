"""Local dashboard: one HTML file you open by double-click, no Notion or claude.ai account needed.

usage: python3 tools/local_dashboard.py [--open]
writes data/dashboard/Job-Dashboard.html (git-ignored: it holds your applications and emails)

Reads the tracker through common.notion_rows(), so it works with both backends (local data/tracker.csv or Notion).
Shows headline numbers, three charts (status, funnel, applications per week) and a table with title, company, status and
applied date. The ⋯ button of a row opens its details: posting link, stage, notes, the emails that belong to it, the JD
snapshot and the documents in its data/applications/<date>_<company>_<title>/ folder.

Emails: every data/mail/**/dump.json (+ its classified_*.json) is merged into data/mail/archive.json, so emails stay
available after the daily dump is overwritten. An email belongs to a row when it is in the row's Gmail thread, or when
its classified company matches the row's company (best title match wins).

The page is fully self-contained (data inlined, no internet needed). Links to JD PDFs and documents are relative, so the
file must stay in data/dashboard/. Rebuild it after a sync or an application; the job-dashboard skill does this.
"""
import glob, html, json, os, re, sys, subprocess
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from common import DATA, ROOT, load_env, notion_rows, same_company, title_sim, gmail_link, load_json, backend, url_key
from stage import reached, ended, FUNNEL
from jd_snapshot import slug

MAIL = os.path.join(DATA, 'mail')
APPS = os.path.join(DATA, 'applications')
OUT = os.path.join(DATA, 'dashboard', 'Job-Dashboard.html')
TEMPLATE = os.path.join(ROOT, 'dashboard', 'local.html')
IGNORE = {'recruiter_outreach', 'account_admin', 'job_alert', 'other', 'viewed', 'incomplete_reminder'}
DOC_LABEL = {'jd.pdf': 'Job description (PDF)', 'page.pdf': 'Posting as printed', 'page.html': 'Posting page (HTML)', 'jd.md': 'Job description (text)',
             'match.md': 'Requirement match', 'changes.md': 'CV changes', 'answers.md': 'Form answers', 'form-answers.md': 'Form answers'}


def hx(i):
    try:
        return f'{int(i):x}'
    except (TypeError, ValueError):
        return ''


def tail(link):
    return (link or '').rsplit('/', 1)[-1].lower()


def iso(d):
    try:
        t = parsedate_to_datetime(d)
        return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone().isoformat(timespec='minutes')
    except (TypeError, ValueError):
        return ''


def mail_archive():
    """msgid -> email with classification, merged from every dump under data/mail and the archive of earlier runs."""
    path = os.path.join(MAIL, 'archive.json')
    arch = {m['msgid']: m for m in load_json(path, []) or []}
    for dump in glob.glob(os.path.join(MAIL, '**', 'dump*.json'), recursive=True):
        d = os.path.dirname(dump)
        cls = {}
        for f in sorted(glob.glob(os.path.join(d, 'classified_*.json'))):
            for c in load_json(f, []) or []:
                if isinstance(c, dict) and c.get('msgid'):
                    cls[c['msgid']] = c
        for m in load_json(dump, []) or []:
            if not isinstance(m, dict) or not m.get('msgid'):
                continue
            old = arch.get(m['msgid'], {})
            c = cls.get(m['msgid']) or {k: old.get(k, '') for k in ('category', 'company', 'title')}
            arch[m['msgid']] = dict(msgid=m['msgid'], thrid=m.get('thrid', ''), date=iso(m.get('date')) or old.get('date', ''),
                                    frm=m.get('frm', ''), subject=m.get('subject', ''), body=(m.get('body') or '')[:3000],
                                    category=c.get('category', ''), company=c.get('company', ''), title=c.get('title', ''))
    out = sorted(arch.values(), key=lambda m: m.get('date', ''))
    os.makedirs(MAIL, exist_ok=True)
    json.dump(out, open(path, 'w'), ensure_ascii=False)
    return out


def attach_mails(rows, mails):
    by_thread = {}
    for r in rows:
        for k in (tail(r.get('thread')), tail(r.get('evidence'))):
            if k:
                by_thread.setdefault(k, r)
    for m in mails:
        r = by_thread.get(hx(m['thrid'])) or by_thread.get(hx(m['msgid']))
        if not r and m.get('category') and m['category'] not in IGNORE and m.get('company'):
            cands = [x for x in rows if same_company(m['company'], x['company'])]
            if len(cands) > 1 and m.get('title'):
                scored = sorted(((title_sim(m['title'], x['title']) or 0, x) for x in cands), key=lambda t: -t[0])
                cands = [scored[0][1]] if scored[0][0] >= 0.5 else []
            elif len(cands) > 1:   # no title: the latest application before the email
                before = [x for x in cands if (x.get('applied') or x.get('first_seen') or '') <= m['date'][:10]]
                cands = sorted(before, key=lambda x: x.get('applied') or x.get('first_seen') or '')[-1:]
            r = cands[0] if cands else None
        if r:
            r['_mails'].append(dict(date=m['date'], frm=m['frm'], subject=m['subject'], body=m['body'], category=m['category'],
                                    link=gmail_link(m['msgid']) if hx(m['msgid']) else ''))


def folders():
    out = []
    for name in sorted(os.listdir(APPS)) if os.path.isdir(APPS) else []:
        parts = name.split('_', 2)
        if len(parts) != 3 or not os.path.isdir(os.path.join(APPS, name)):
            continue
        meta = {}
        jd = os.path.join(APPS, name, 'jd.md')
        if os.path.exists(jd):
            head = open(jd, encoding='utf-8', errors='replace').read(3000)
            m = re.match(r'---\n(.*?)\n---', head, re.S)
            if m:
                meta = dict(re.findall(r'^(\w+):\s*(.*)$', m.group(1), re.M))
        out.append(dict(name=name, date=parts[0], company=parts[1].lower(), title=parts[2].lower(), url=url_key(meta.get('url', '')),
                        co_text=meta.get('company') or parts[1].replace('-', ' '), title_text=meta.get('title') or parts[2].replace('-', ' ')))
    return out


def find_folder(r, fl):
    """Same posting URL (from jd.md) → same slugs → same company with a similar title. Closest date wins."""
    u = url_key(r.get('url'))
    hits = [f for f in fl if u and f['url'] == u]
    if not hits:
        c, t = slug(r['company'], 30).lower(), slug(r['title']).lower()
        hits = [f for f in fl if f['company'] == c and (f['title'] == t or f['title'][:20] == t[:20])]
    if not hits:
        hits = [f for f in fl if same_company(r['company'], f['co_text']) and (title_sim(r['title'], f['title_text']) or 0) >= 0.75
                and not (u and f['url'] and f['url'] != u)]
    if not hits:
        return None
    day = r.get('applied') or (r.get('first_seen') or '')[:10]
    return min(hits, key=lambda f: abs((datetime.fromisoformat(f['date']) - datetime.fromisoformat(day)).days) if day else 0)['name']


def docs(name):
    base = os.path.join(APPS, name)
    files, jd = [], ''
    for f in sorted(os.listdir(base)):
        if f.startswith('.') or f.endswith(('.yaml', '.tmp')):
            continue
        files.append(dict(name=f, label=DOC_LABEL.get(f, f), href=f'../applications/{quote(name)}/{quote(f)}'))
    p = os.path.join(base, 'jd.md')
    if os.path.exists(p):
        txt = open(p, encoding='utf-8', errors='replace').read()
        meta = re.match(r'---\n(.*?)\n---\n', txt, re.S)
        status = re.search(r'page_status:\s*(\w+)', meta.group(1)).group(1) if meta and 'page_status' in meta.group(1) else ''
        jd = dict(text=txt[meta.end():].strip()[:20000] if meta else txt[:20000], status=status)
    order = ['jd.pdf', 'page.pdf', 'page.html']
    files.sort(key=lambda d: (order.index(d['name']) if d['name'] in order else 9, d['name']))
    return files, jd


def main():
    env = load_env()
    rows = notion_rows(env)
    for r in rows:
        r['_mails'] = []
    attach_mails(rows, mail_archive())
    fl = folders()
    out = []
    for r in rows:
        name = find_folder(r, fl)
        files, jd = docs(name) if name else ([], '')
        applied = bool(r.get('applied'))
        out.append(dict(id=r['id'], title=r['title'], company=r['company'], city=r['city'], salary=r['salary'], platform=r['platform'] or 'Other',
                        status=r['status'], stage=r['stage'], source=r['source'], applied=r['applied'], applied_text=r['applied_text'],
                        first_seen=(r.get('first_seen') or '')[:10], interview_date=r['interview_date'], last_email=r['last_email'],
                        url=r['url'], notion_url=r['notion_url'], notes=r['notes'], events=r['events'], mode=r['mode'], cv=r['cv_version'],
                        cover_letter=r['cover_letter'], posted=r['posted'], folder=name or '', files=files, jd=jd,
                        mails=sorted(r['_mails'], key=lambda m: m['date'], reverse=True),
                        funnel=[s for s in FUNNEL if applied and reached(r, s)], ended=ended(r)))
    data = dict(generated=datetime.now().isoformat(timespec='minutes'), backend=backend(env), rows=out)
    page = open(TEMPLATE, encoding='utf-8').read()
    blob = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    page = page.replace('/*__DATA__*/null', blob, 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(page)
    n_mail = sum(len(r['mails']) for r in out); n_docs = sum(1 for r in out if r['folder'])
    print(f"{len(out)} rows, {n_mail} emails attached, {n_docs} with documents -> {OUT}")
    if '--open' in sys.argv:
        if sys.platform == 'darwin':
            subprocess.run(['open', OUT])
        elif os.name == 'nt':
            os.startfile(OUT)   # noqa
        else:
            subprocess.run(['xdg-open', OUT])


if __name__ == '__main__':
    main()
