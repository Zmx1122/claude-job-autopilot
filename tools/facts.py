"""Fact bank helper — knowledge/career/facts.yaml is the single source of truth for CVs and cover letters.

usage:
  python3 tools/facts.py check                 validate ids, dates, evidence; list unconfirmed facts and open questions
  python3 tools/facts.py durations             canonical duration of every dated entry (EN / DE / ZH) — quote these, never round
  python3 tools/facts.py seed [--out PATH]     draft entries from knowledge/manifest.yaml (degrees, references, awards …),
                                               all confirmed: false — the starting point when the user has no CV
Evidence values: a manifest id, an entry/achievement id of this file, or interview:YYYY-MM-DD
(raw answers in knowledge/career/interviews/YYYY-MM-DD.md).
"""
import os, re, sys
from datetime import date
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = os.path.join(ROOT, 'knowledge', 'career', 'facts.yaml')
MANIFEST = os.path.join(ROOT, 'knowledge', 'manifest.yaml')
INTERVIEWS = os.path.join(ROOT, 'knowledge', 'career', 'interviews')
YM = re.compile(r'^(\d{4})-(\d{2})$')


def load(path=FACTS):
    if not os.path.exists(path):
        raise SystemExit(f'{os.path.relpath(path, ROOT)} not found — run the job-career-coach skill (or `facts.py seed`) first.')
    return yaml.safe_load(open(path)) or {}


def manifest_ids():
    if not os.path.exists(MANIFEST):
        return set()
    return {d['id'] for d in (yaml.safe_load(open(MANIFEST)) or {}).get('documents', [])}


def ym(v):
    """'2022-01' → (2022, 1); 'present' → today. Accepts YYYY-MM only (dates are stored to the month)."""
    if v in (None, ''):
        return None
    if str(v).lower() in ('present', 'heute', 'now'):
        t = date.today(); return (t.year, t.month)
    m = YM.match(str(v))
    return (int(m.group(1)), int(m.group(2))) if m else 'bad'


def months(e):
    s, t = ym(e.get('start')), ym(e.get('end'))
    if not s or not t or 'bad' in (s, t):
        return None
    return (t[0] - s[0]) * 12 + (t[1] - s[1]) + 1   # inclusive: 01/2022–03/2024 = 27 months


def say(n):
    y, m = divmod(n, 12)
    en = ' '.join(p for p in (f'{y} year' + ('s' if y != 1 else '') if y else '', f'{m} month' + ('s' if m != 1 else '') if m else '') if p)
    de = ' '.join(p for p in (f'{y} Jahr' + ('e' if y != 1 else '') if y else '', f'{m} Monat' + ('e' if m != 1 else '') if m else '') if p)
    zh = (f'{y} 年' if y else '') + (f' {m} 个月' if m else '')
    return en, de, zh.strip()


def durations(f=None):
    """[(entry, months)] for every entry with start and end."""
    f = f or load()
    return [(e, months(e)) for e in f.get('entries', []) if months(e)]


def check(f):
    errors, warns = [], []
    man = manifest_ids()
    ids = {}
    for e in f.get('entries', []):
        ids.setdefault(e.get('id'), 0); ids[e.get('id')] += 1
        for a in e.get('achievements') or []:
            ids.setdefault(a.get('id'), 0); ids[a.get('id')] += 1
    for k, n in ids.items():
        if not k: errors.append('an entry or achievement has no id')
        elif n > 1: errors.append(f'duplicate id {k}')

    def ev_ok(where, ev):
        if not ev:
            errors.append(f'{where}: no evidence')
        for x in ev or []:
            x = str(x)
            if x.startswith('interview:'):
                d = x.split(':', 1)[1]
                if not os.path.exists(os.path.join(INTERVIEWS, f'{d}.md')):
                    warns.append(f'{where}: {x} has no notes file knowledge/career/interviews/{d}.md')
            elif x not in man and x not in ids:
                errors.append(f'{where}: evidence "{x}" is neither a manifest id, a fact id nor interview:YYYY-MM-DD')

    unconfirmed = []
    for e in f.get('entries', []):
        w = e.get('id', '?')
        for k in ('start', 'end'):
            if ym(e.get(k)) == 'bad':
                errors.append(f'{w}: {k} "{e.get(k)}" is not YYYY-MM or present')
        s, t = ym(e.get('start')), ym(e.get('end'))
        if s and t and 'bad' not in (s, t) and s > t:
            errors.append(f'{w}: start after end')
        if e.get('type') == 'education' and e.get('status') not in ('completed', 'ongoing', 'discontinued'):
            warns.append(f'{w}: education status should be completed | ongoing | discontinued (CV rule 11)')
        ev_ok(w, e.get('evidence'))
        if not e.get('confirmed'): unconfirmed.append(w)
        for a in e.get('achievements') or []:
            ev_ok(f"{w}/{a.get('id')}", a.get('evidence'))
            if not a.get('confirmed'): unconfirmed.append(f"{w}/{a.get('id')}")
    for g in f.get('skills') or []:
        ev_ok(f"skills/{g.get('group')}", g.get('evidence'))
    for l in f.get('languages') or []:
        ev_ok(f"languages/{l.get('language')}", l.get('evidence'))
    openq = [q for q in f.get('open_questions') or [] if q.get('status', 'open') == 'open']
    return errors, warns, unconfirmed, openq


def seed(out):
    if os.path.exists(out):
        raise SystemExit(f'{out} exists — edit it instead of seeding again.')
    docs = (yaml.safe_load(open(MANIFEST)) or {}).get('documents', []) if os.path.exists(MANIFEST) else []
    if not docs:
        raise SystemExit('knowledge/manifest.yaml is empty — build the knowledge base first (job-knowledge-base skill).')
    TYPE = {'degree': 'education', 'transcript': 'education', 'work_reference': 'work', 'reference_letter': 'work',
            'award': 'award', 'certificate': 'certificate', 'language_certificate': 'certificate', 'publication': 'publication'}
    entries, langs = [], []
    for d in docs:
        t = TYPE.get(d.get('kind'))
        if not t:
            continue
        fx = d.get('facts') or {}
        period = str(fx.get('period', ''))
        dates = re.findall(r'(\d{4})-(\d{2})', period)
        e = {'id': f"{t}-{d['id']}", 'type': t, 'role': fx.get('role') or fx.get('degree') or d.get('title'),
             'org': d.get('issuer'), 'start': '-'.join(dates[0]) if dates else '', 'end': '-'.join(dates[-1]) if len(dates) > 1 else str(d.get('date') or ''),
             'evidence': [d['id']], 'confirmed': False, 'from_document': fx, 'proves': d.get('proves') or []}
        if t == 'education':
            e.update(status='completed' if d.get('kind') == 'degree' else '', grade=str(fx.get('overall_grade') or fx.get('grade') or ''))
        if d.get('kind') == 'language_certificate':
            langs.append({'language': fx.get('language', ''), 'level': fx.get('level', ''), 'evidence': [d['id']]})
        entries.append(e)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    yaml.safe_dump({'version': 1, 'headline_options': [], 'entries': entries, 'skills': [], 'languages': langs,
                    'open_questions': []}, open(out, 'w'), allow_unicode=True, sort_keys=False, width=120)
    print(f'seeded {len(entries)} draft entries → {os.path.abspath(out)} (all confirmed: false). '
          'Merge education/transcript pairs, then interview the user to fill roles, achievements and skills.')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'seed':
        seed(sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else FACTS)
    elif cmd == 'durations':
        for e, n in durations():
            en, de, zh = say(n)
            print(f"{e['id']:<28} {e.get('start')}–{e.get('end')}  {n:>3} months · {en} · {de} · {zh}")
    elif cmd == 'check':
        errors, warns, unconfirmed, openq = check(load())
        for x in errors: print('❌', x)
        for x in warns: print('⚠️ ', x)
        if unconfirmed: print(f'⏳ not confirmed by the user ({len(unconfirmed)}), never used in documents: ' + ', '.join(unconfirmed))
        for q in openq: print(f"❓ {q.get('id')}: {q.get('question')}")
        print('fact bank ok' if not errors else f'{len(errors)} error(s)')
        sys.exit(1 if errors else 0)
    else:
        raise SystemExit(__doc__)
