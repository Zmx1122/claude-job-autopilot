"""Local tracker: the job applications table as a CSV file, for users without Notion.

The file is data/tracker.csv (git-ignored, backed up with the rest of data/). It opens in Excel or Numbers, but the
scripts own it: close it in Excel before a sync, and do not rename the columns. Deleted rows go to data/tracker_trash.csv.

Nothing calls this module directly. common.py switches to it when TRACKER_BACKEND=local is set in .env (or when no
Notion token is configured): notion_rows() reads the CSV, and notion_call() turns the Notion page requests that the
scripts already send (create page, update properties, move to trash) into CSV edits. So log_application.py,
sync_mail.py, prune_shortlisted.py, dedupe.py, jd_snapshot.py and dashboard_data.py work unchanged.

usage (self-test on a temporary file): python3 tools/tracker_local.py
"""
import csv, json, os, re, uuid
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.environ.get('JA_TRACKER_FILE') or os.path.join(ROOT, 'data', 'tracker.csv')

# Notion property name -> (row field, Notion type). Same columns as the Notion database (tools/notion_setup.py).
PROPS = {
    'Title': ('title', 'title'), 'Company': ('company', 'rich_text'), 'City': ('city', 'rich_text'),
    'Salary Range': ('salary', 'rich_text'), 'Platform': ('platform', 'select'), 'Status': ('status', 'select'),
    'Source': ('source', 'select'), 'Applied On': ('applied_text', 'rich_text'), 'Stage': ('stage', 'select'),
    'Interview Date': ('interview_date', 'date'), 'First Seen': ('first_seen', 'date'), 'Last Email': ('last_email', 'date'),
    'URL': ('url', 'url'), 'Email Evidence': ('evidence', 'url'), 'Email Thread': ('thread', 'url'),
    'Job ID': ('job_id', 'rich_text'), 'Events': ('events', 'rich_text'), 'Notes': ('notes', 'rich_text'),
    'Mode': ('mode', 'select'), 'CV Version': ('cv_version', 'rich_text'), 'Cover Letter': ('cover_letter', 'checkbox'),
    'Posted': ('posted', 'date'),
}
COLUMNS = ['id'] + [f for f, _ in PROPS.values()] + ['created', 'updated']


def schema():
    """{column name: Notion type}, like common.db_props() returns for a Notion database."""
    return {k: t for k, (_, t) in PROPS.items()}


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8-sig') as f:
        return [dict(r) for r in csv.DictReader(f)]


def _write(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    # utf-8-sig: Excel then shows umlauts and Chinese correctly
    with open(tmp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
        w.writeheader()
        w.writerows({c: r.get(c, '') for c in COLUMNS} for r in rows)
    try:
        os.replace(tmp, path)
    except PermissionError:
        os.remove(tmp)
        raise SystemExit(f'{path} is locked (open in Excel?). Close it and run again.')


def _iso_day(s):
    return s[:10] if re.match(r'\d{4}-\d\d-\d\d', s or '') else ''


def flat(r):
    """CSV row -> the same dict common.flatten() makes from a Notion page."""
    d = {f: r.get(f, '') or '' for f in COLUMNS}
    d['cover_letter'] = str(d['cover_letter']).lower() in ('true', '1', 'yes', 'x')
    d['applied'] = _iso_day(d['applied_text'])
    d['notion_url'] = ''
    return d


def rows(path=None):
    return [flat(r) for r in _read(path or PATH)]


def _value(v, kind):
    """Notion property value -> plain string (or bool for checkbox)."""
    if v is None:
        return ''
    if kind in ('title', 'rich_text'):
        return ''.join((t.get('text') or {}).get('content', '') or t.get('plain_text', '') for t in v.get(kind) or [])
    if kind == 'select':
        return ((v.get('select') or {}).get('name')) or ''
    if kind == 'date':
        return ((v.get('date') or {}).get('start')) or ''
    if kind == 'url':
        return v.get('url') or ''
    if kind == 'checkbox':
        return bool(v.get('checkbox'))
    return ''


def from_props(props):
    out = {}
    for name, v in (props or {}).items():
        if name in PROPS:
            field, kind = PROPS[name]
            out[field] = _value(v, kind)
    return out


class Resp:
    """Enough of requests.Response for the scripts: status_code, text, json()."""
    def __init__(self, code, payload):
        self.status_code, self._p = code, payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self):
        return self._p


def call(method, url, body=None, path=None):
    """Handle a Notion API request against the CSV. Supports what the scripts use."""
    path = path or PATH
    body = body or {}
    now = datetime.now().isoformat(timespec='seconds')
    if method == 'GET' and '/databases/' in url:
        return Resp(200, {'object': 'database', 'properties': {k: {'type': t} for k, t in schema().items()}})
    if method == 'POST' and url.rstrip('/').endswith('/pages'):
        data = _read(path)
        row = {c: '' for c in COLUMNS}
        row.update(from_props(body.get('properties')))
        row.update(id=str(uuid.uuid4()), created=now, updated=now)
        data.append(row)
        _write(data, path)
        return Resp(200, {'object': 'page', 'id': row['id']})
    m = re.search(r'/pages/([\w-]+)$', url)
    if method == 'PATCH' and m:
        pid = m.group(1)
        data = _read(path)
        hit = next((r for r in data if r.get('id') == pid), None)
        if not hit:
            return Resp(404, {'object': 'error', 'message': f'row {pid} not found in {path}'})
        if body.get('in_trash') or body.get('archived'):
            trash = os.path.join(os.path.dirname(path), 'tracker_trash.csv')
            hit['updated'] = now
            _write(_read(trash) + [hit], trash)
            _write([r for r in data if r is not hit], path)
            return Resp(200, {'object': 'page', 'id': pid, 'in_trash': True})
        hit.update(from_props(body.get('properties')))
        hit['updated'] = now
        _write(data, path)
        return Resp(200, {'object': 'page', 'id': pid})
    return Resp(400, {'object': 'error', 'message': f'local tracker does not support {method} {url}'})


def import_rows(flat_rows, path=None):
    """Write Notion rows (common.flatten dicts) into the CSV, keeping their ids. Used by tools/tracker.py import-notion."""
    now = datetime.now().isoformat(timespec='seconds')
    out = []
    for r in flat_rows:
        row = {c: r.get(c, '') for c in COLUMNS}
        row['cover_letter'] = 'true' if r.get('cover_letter') else ''
        row['created'] = row['created'] or r.get('first_seen') or now
        row['updated'] = now
        out.append(row)
    _write(out, path or PATH)
    return len(out)


if __name__ == '__main__':
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), 'tracker.csv')
    r = call('POST', 'https://api.notion.com/v1/pages', {'parent': {'database_id': 'x'}, 'properties': {
        'Title': {'title': [{'text': {'content': 'AI Engineer (m/w/d)'}}]}, 'Company': {'rich_text': [{'text': {'content': 'Müller AG'}}]},
        'Status': {'select': {'name': 'Applied'}}, 'Applied On': {'rich_text': [{'text': {'content': '2026-11-16'}}]},
        'Cover Letter': {'checkbox': True}}}, path=p)
    pid = r.json()['id']
    assert rows(p)[0]['company'] == 'Müller AG' and rows(p)[0]['applied'] == '2026-11-16' and rows(p)[0]['cover_letter'] is True
    call('PATCH', f'https://api.notion.com/v1/pages/{pid}', {'properties': {'Stage': {'select': {'name': '一面邀请'}}, 'Interview Date': {'date': None}}}, path=p)
    assert rows(p)[0]['stage'] == '一面邀请'
    assert call('GET', 'https://api.notion.com/v1/databases/x', path=p).json()['properties']['Applied On']['type'] == 'rich_text'
    call('PATCH', f'https://api.notion.com/v1/pages/{pid}', {'in_trash': True}, path=p)
    assert rows(p) == [] and len(rows(os.path.join(os.path.dirname(p), 'tracker_trash.csv'))) == 1
    print('ok')
