"""Create the "Job Applications" database under NOTION_PARENT_PAGE_ID and store its id in .env.

usage: python3 tools/notion_setup.py [--force]
Safe to re-run: if NOTION_DATABASE_ID is already set and reachable, it only verifies the schema and adds missing columns.
"""
import re, sys, requests
from common import load_env, set_env_value, notion_headers

SELECT = lambda opts: {'select': {'options': [{'name': n, 'color': c} for n, c in opts]}}
SCHEMA = {
    'Title': {'title': {}},
    'Company': {'rich_text': {}},
    'City': {'rich_text': {}},
    'Salary Range': {'rich_text': {}},
    'First Seen': {'date': {}},
    'Applied On': {'date': {}},
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
}


def page_id(s):
    """Accept a raw id or a full Notion URL and return the dashed 32-hex id."""
    m = re.findall(r'[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}', s or '')
    if not m:
        raise SystemExit('NOTION_PARENT_PAGE_ID is empty or not a Notion page id / link.')
    h = m[-1].replace('-', '')
    return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}'


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
