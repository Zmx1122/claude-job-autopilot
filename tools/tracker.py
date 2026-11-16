"""Which tracker is in use (Notion or the local CSV), and moving rows from Notion to the local CSV.

usage: python3 tools/tracker.py status           which backend, how many rows, where the file is
       python3 tools/tracker.py import-notion    copy every Notion row into data/tracker.csv (asks before replacing a non-empty file;
                                                 add --yes to skip the question), then set TRACKER_BACKEND=local in .env yourself

The backend is chosen in .env: TRACKER_BACKEND=local or TRACKER_BACKEND=notion. Without the line: Notion when NOTION_TOKEN
and NOTION_DATABASE_ID are filled in, else local. See tools/tracker_local.py.
"""
import os, sys
from collections import Counter
from common import load_env, backend, notion_rows
import tracker_local

cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
env = load_env()
if cmd == 'status':
    b = backend(env)
    rows = notion_rows(env)
    where = tracker_local.PATH if b == 'local' else f"Notion database {env.get('NOTION_DATABASE_ID', '')[:8]}…"
    print(f'backend: {b} ({where})\nrows: {len(rows)}  ' + ', '.join(f'{k or "(none)"} {v}' for k, v in Counter(r["status"] for r in rows).most_common()))
elif cmd == 'import-notion':
    if not (env.get('NOTION_TOKEN') and env.get('NOTION_DATABASE_ID')):
        raise SystemExit('NOTION_TOKEN and NOTION_DATABASE_ID are needed in .env to read the Notion database.')
    have = tracker_local.rows()
    if have and '--yes' not in sys.argv:
        if input(f'{tracker_local.PATH} already has {len(have)} rows. Replace them? [y/N] ').strip().lower() != 'y':
            raise SystemExit('nothing changed')
    n = tracker_local.import_rows(notion_rows(dict(env, TRACKER_BACKEND='notion')))
    print(f'{n} rows copied to {tracker_local.PATH}. To use it from now on, set TRACKER_BACKEND=local in .env.')
else:
    raise SystemExit(__doc__)
