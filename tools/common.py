"""Shared helpers: paths, .env / profile loading, Notion + IMAP clients, company/title matching."""
import os, re, json, time, imaplib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
os.makedirs(DATA, exist_ok=True)
NOTION_VERSION = '2022-06-28'


def env_path():
    # JA_ENV_FILE lets you point at a .env outside the repo (useful for testing).
    return os.environ.get('JA_ENV_FILE') or os.path.join(ROOT, '.env')


def load_env():
    env = {}
    p = env_path()
    if not os.path.exists(p):
        raise SystemExit(f'.env not found at {p}. Copy .env.example to .env first (the setup skill does this for you).')
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def set_env_value(key, value):
    """Write or replace KEY=value in .env (used by setup scripts to store generated ids)."""
    p = env_path()
    lines = open(p).read().splitlines() if os.path.exists(p) else []
    for i, line in enumerate(lines):
        if line.split('=', 1)[0].strip() == key:
            lines[i] = f'{key}={value}'
            break
    else:
        lines.append(f'{key}={value}')
    open(p, 'w').write('\n'.join(lines) + '\n')


def load_profile():
    import yaml  # pyyaml
    p = os.path.join(ROOT, 'config', 'profile.yaml')
    if not os.path.exists(p):
        raise SystemExit('config/profile.yaml not found. Run the setup skill (questionnaire) first.')
    return yaml.safe_load(open(p))


# ---------- Notion ----------
def notion_headers(env, json_body=True):
    h = {'Authorization': f"Bearer {env['NOTION_TOKEN']}", 'Notion-Version': NOTION_VERSION}
    if json_body:
        h['Content-Type'] = 'application/json'
    return h


def notion_rows(env):
    """All pages of the Job Applications database as flat dicts."""
    import requests
    H = notion_headers(env)
    rows, cursor = [], None
    while True:
        body = {'page_size': 100, **({'start_cursor': cursor} if cursor else {})}
        d = requests.post(f"https://api.notion.com/v1/databases/{env['NOTION_DATABASE_ID']}/query", headers=H, json=body).json()
        if 'results' not in d:
            raise SystemExit(f'Notion query failed: {d}')
        for p in d['results']:
            rows.append(flatten(p))
        if not d.get('has_more'):
            return rows
        cursor = d['next_cursor']


def flatten(p):
    pr = p['properties']
    def txt(k): return ''.join(t['plain_text'] for t in (pr.get(k) or {}).get('rich_text', []))
    def ttl(k): return ''.join(t['plain_text'] for t in (pr.get(k) or {}).get('title', []))
    def sel(k): return ((pr.get(k) or {}).get('select') or {}).get('name', '')
    def dt(k): return (((pr.get(k) or {}).get('date') or {}).get('start') or '')
    def url(k): return (pr.get(k) or {}).get('url') or ''
    def chk(k): return bool((pr.get(k) or {}).get('checkbox'))
    # Applied On is a text column ("2026-11-10", or "放弃投递" for jobs never applied to); older databases have a date column.
    applied_text = dt('Applied On') or txt('Applied On')
    return dict(id=p['id'], notion_url=p.get('url', ''), title=ttl('Title'), company=txt('Company'), city=txt('City'), salary=txt('Salary Range'),
                platform=sel('Platform'), status=sel('Status'), source=sel('Source'), applied=iso_day(applied_text), applied_text=applied_text,
                stage=sel('Stage'), interview_date=dt('Interview Date'), first_seen=dt('First Seen'),
                last_email=dt('Last Email'), url=url('URL'), evidence=url('Email Evidence'), thread=url('Email Thread'),
                job_id=txt('Job ID'), events=txt('Events'), notes=txt('Notes'),
                mode=sel('Mode'), cv_version=txt('CV Version'), cover_letter=chk('Cover Letter'), posted=dt('Posted'))


def rt(s):
    return {'rich_text': [{'text': {'content': (s or '')[:1900]}}]}


def iso_day(s):
    """'2026-11-10' (or a longer ISO timestamp) → '2026-11-10'; anything else (e.g. '放弃投递') → ''."""
    return s[:10] if re.match(r'\d{4}-\d\d-\d\d', s or '') else ''


NOT_APPLIED = '放弃投递'   # Applied On text for jobs that were never applied to
_DB_PROPS = {}


def db_props(env):
    """{column name: type} of the applications database (cached)."""
    if not _DB_PROPS:
        r = notion_call('GET', f"https://api.notion.com/v1/databases/{env['NOTION_DATABASE_ID']}", env)
        _DB_PROPS.update({k: v['type'] for k, v in r.json().get('properties', {}).items()})
    return _DB_PROPS


def applied_value(env, v):
    """Notion value for Applied On: text column (new) or date column (databases not migrated yet)."""
    if db_props(env).get('Applied On') == 'date':
        return {'date': {'start': iso_day(v)}} if iso_day(v) else {'date': None}
    return rt(v)


def notion_call(method, url, env, **kw):
    import requests
    for attempt in range(4):
        r = requests.request(method, url, headers=notion_headers(env), **kw)
        if r.status_code == 429:
            time.sleep(1 + attempt)
            continue
        return r
    return r


# ---------- Gmail / IMAP ----------
ALL_MAIL_CANDIDATES = ['"[Gmail]/All Mail"', '"[Gmail]/Alle Nachrichten"', '"[Google Mail]/All Mail"', '"[Google Mail]/Alle Nachrichten"']


def imap_login(env, readonly=True):
    M = imaplib.IMAP4_SSL(env.get('IMAP_HOST', 'imap.gmail.com'), int(env.get('IMAP_PORT', 993)))
    M.login(env['IMAP_USER'], env['IMAP_APP_PASSWORD'].replace(' ', ''))
    # Gmail localizes the All Mail folder name; find it by its \All flag first.
    typ, boxes = M.list()
    for b in boxes or []:
        line = b.decode(errors='replace')
        if '\\All' in line:
            name = line.split(' "/" ')[-1]
            M.select(name, readonly=readonly)
            return M
    for name in ALL_MAIL_CANDIDATES:
        if M.select(name, readonly=readonly)[0] == 'OK':
            return M
    raise SystemExit('Could not open the All Mail folder. Is IMAP enabled in Gmail settings?')


def gmail_link(id_int):
    return f"https://mail.google.com/mail/u/0/#all/{int(id_int):x}"


def label_name(env):
    return env.get('GMAIL_LABEL') or 'applications'


# ---------- matching ----------
LEGAL = r'\b(gmbh|ag|se|kg|co|ltd|inc|holding|group|gruppe|germany|deutschland|europe|limited|consulting|recruiting|recruitment|solutions|services|unternehmensgruppe|partners|team)\b'


def norm_company(c):
    c = (c or '').lower()
    c = re.sub(r'[^\w\s]', ' ', c)
    c = re.sub(LEGAL, ' ', c)
    return re.sub(r'\s+', ' ', c).strip()


def url_key(u):
    """Posting URL for comparisons: drops tracking query parameters but keeps the ones that ARE the job id
    (Indeed viewjob?jk=…, LinkedIn currentJobId=…). Stripping the whole query made every Indeed posting equal (2026-11-11)."""
    base, _, q = (u or '').strip().partition('?')
    keep = sorted(p for p in q.split('&') if p.split('=')[0] in ('jk', 'vjk', 'currentJobId', 'jobId', 'gh_jid'))
    return base.rstrip('/') + ('?' + '&'.join(keep) if keep else '')


def same_company(a, b):
    na, nb = norm_company(a), norm_company(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # compare with and without spaces ("Auto Scout24" == "AutoScout24")
    for x, y in ((na, nb), (na.replace(' ', ''), nb.replace(' ', ''))):
        short, long_ = (x, y) if len(x) <= len(y) else (y, x)
        if len(short) >= 4 and short in long_:
            return True
    A = {t for t in na.split() if len(t) >= 3}
    B = {t for t in nb.split() if len(t) >= 3}
    if A and B and (A <= B or B <= A):
        return True
    # same distinctive brand word first ("finanzen.net zero" vs "finanzen.net (Finanzen invest)")
    fa, fb = na.split()[0], nb.split()[0]
    return fa == fb and len(fa) >= 5


STOP = {'senior', 'junior', 'm', 'w', 'd', 'f', 'x', 'gn', 'und', 'and', 'the', 'for', 'mit', 'in', 'der', 'die', 'das', 'bei', 'at', 'all', 'genders', 'human', 'mwd'}


def title_tokens(t):
    t = (t or '').lower()
    t = re.sub(r'\([^)]*\)', ' ', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    return set(w for w in t.split() if w not in STOP)


def title_sim(a, b):
    """Token overlap; capped below 0.5 when the overlap covers less than half of the longer title."""
    A, B = title_tokens(a), title_tokens(b)
    if not A or not B:
        return None
    ov = len(A & B)
    if ov / max(len(A), len(B)) < 0.5:
        return min(ov / min(len(A), len(B)), 0.49)
    return ov / min(len(A), len(B))


def load_json(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default
