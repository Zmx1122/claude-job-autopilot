"""Create the "Job Applications" database under NOTION_PARENT_PAGE_ID and store its id in .env.

usage: python3 tools/notion_setup.py [--force]
Safe to re-run: if NOTION_DATABASE_ID is already set and reachable, it only verifies the schema and adds missing columns.
It also migrates older databases: "Applied On" date → text (so rows never applied to can say "放弃投递"), existing dates are
rewritten as "YYYY-MM-DD". Back up first (python3 tools/backup.py save); the column keeps its id, so views keep their sort.
"""
import re, sys, time, requests
from common import load_env, set_env_value, notion_headers, notion_rows, notion_call, rt
from stage import STAGES, color

SELECT = lambda opts: {'select': {'options': [{'name': n, 'color': c} for n, c in opts]}}
SCHEMA = {
    'Title': {'title': {}},
    'Company': {'rich_text': {}},
    'City': {'rich_text': {}},
    'Salary Range': {'rich_text': {}},
    'First Seen': {'date': {}},
    'Applied On': {'rich_text': {}},
    'Applied Date': {'date': {}},          # same date as Applied On, as a real date (native Notion charts)
    'Applied Week': {'formula': {'expression': 'if(empty(prop("Applied Date")), "", formatDate(prop("Applied Date"), "GGGG-[W]WW"))'}},
    'Stage': {'select': {'options': [{'name': n, 'color': color(n)} for n in STAGES]}},
    'Interview Date': {'date': {}},
    'Last Email': {'date': {}},
    'Platform': SELECT([('LinkedIn', 'blue'), ('Indeed', 'purple'), ('StepStone', 'orange'), ('Xing', 'green'), ('Other', 'gray')]),
    'Status': SELECT([('Seen', 'gray'), ('Shortlisted', 'yellow'), ('Applied', 'blue'), ('Confirmed', 'purple'), ('Interview', 'orange'),
                      ('Offer', 'green'), ('Rejected', 'red'), ('Skipped', 'default'), ('Withdrawn', 'brown')]),
    'Source': SELECT([('auto', 'blue'), ('manual', 'yellow')]),
    'URL': {'url': {}},
    'Email Evidence': {'url': {}},
    'Email Thread': {'url': {}},
    'Job ID': {'rich_text': {}},
    'Events': {'rich_text': {}},
    'Notes': {'rich_text': {}},
    'Mode': SELECT([('tailored', 'pink'), ('template', 'blue')]),
    'CV Version': {'rich_text': {}},
    'Cover Letter': {'checkbox': {}},
    'Posted': {'date': {}},
}


def page_id(s):
    """Accept a raw id or a full Notion URL and return the dashed 32-hex id."""
    m = re.findall(r'[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}', s or '')
    if not m:
        raise SystemExit('NOTION_PARENT_PAGE_ID is empty or not a Notion page id / link.')
    h = m[-1].replace('-', '')
    return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}'


def migrate_applied_on(env, db, H):
    """Applied On: date column → text column, values rewritten as YYYY-MM-DD."""
    rows = notion_rows(env)
    dates = {r['id']: r['applied'] for r in rows if r['applied']}
    r = requests.patch(f'https://api.notion.com/v1/databases/{db}', headers=H, json={'properties': {'Applied On': {'rich_text': {}}}})
    if r.status_code != 200:
        raise SystemExit(f'Applied On: type change failed {r.status_code}: {r.text[:300]}')
    for pid, d in dates.items():
        x = notion_call('PATCH', f'https://api.notion.com/v1/pages/{pid}', env, json={'properties': {'Applied On': rt(d)}})
        if x.status_code != 200: print('ERR', pid, x.status_code, x.text[:200])
        time.sleep(0.34)
    print(f'Applied On is now a text column; {len(dates)} dates rewritten as YYYY-MM-DD')


def fill_applied_date(env):
    """New Applied Date column: copy every ISO date from Applied On."""
    n = 0
    for r in notion_rows(env):
        if r['applied']:
            x = notion_call('PATCH', f"https://api.notion.com/v1/pages/{r['id']}", env, json={'properties': {'Applied Date': {'date': {'start': r['applied']}}}})
            if x.status_code != 200: print('ERR', r['id'], x.status_code, x.text[:200])
            n += 1; time.sleep(0.34)
    print(f'Applied Date filled for {n} rows')


def main():
    env = load_env(); H = notion_headers(env)
    parent = page_id(env.get('NOTION_PARENT_PAGE_ID'))
    r = requests.get(f'https://api.notion.com/v1/pages/{parent}', headers=H)
    if r.status_code != 200:
        raise SystemExit(f'Cannot open the parent page ({r.status_code}). In Notion open the page → ••• → Connections → add your integration. Details: {r.text[:200]}')
    set_env_value('NOTION_PARENT_PAGE_ID', parent)
    db = env.get('NOTION_DATABASE_ID', '').strip()
    if db and '--force' not in sys.argv:
        r = requests.get(f'https://api.notion.com/v1/databases/{db}', headers=H)
        if r.status_code == 200:
            have = r.json()['properties']
            missing = {k: v for k, v in SCHEMA.items() if k not in have}
            if missing:
                requests.patch(f'https://api.notion.com/v1/databases/{db}', headers=H, json={'properties': missing})
            print(f'database ok ({db}); added columns: {list(missing) or "none"}')
            if have.get('Applied On', {}).get('type') == 'date':
                migrate_applied_on(env, db, H)
            if 'Applied Date' in missing:
                fill_applied_date(env)
            return
        print('stored NOTION_DATABASE_ID is not reachable, creating a new database')
    body = {'parent': {'type': 'page_id', 'page_id': parent}, 'is_inline': True,
            'title': [{'type': 'text', 'text': {'content': 'Job Applications'}}], 'properties': SCHEMA}
    r = requests.post('https://api.notion.com/v1/databases', headers=H, json=body)
    if r.status_code != 200:
        raise SystemExit(f'create failed {r.status_code}: {r.text[:300]}')
    db = r.json()['id']
    set_env_value('NOTION_DATABASE_ID', db)
    print(f'created database {db} → saved to .env')


if __name__ == '__main__':
    main()
