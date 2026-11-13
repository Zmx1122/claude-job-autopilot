"""Delete tracker rows that stayed "Shortlisted" for more than N days (default 2): the user never picked them.

usage: python3 tools/prune_shortlisted.py [--days 2] [--apply]
Without --apply it only lists the rows it would delete (dry run).
"Delete" = move the Notion page to the trash (Notion keeps it 30 days, restorable from Trash); data/applied.csv keeps its log line.
Age is counted from "First Seen" (the scan date). Rows without First Seen are left alone.
Runs in the daily routine right after the mail sync (job-mail-sync skill, daily mode), before the scan.

Why: the user wants the tracker to hold only jobs that were decided (applied, skipped, in process), not a pile of old
shortlist entries (2026-11-13). A deleted job can come back in a later scan only while its posting is still inside the
posting window; with the default 2-day window it is already too old by then.
"""
import argparse
from datetime import date, timedelta
from common import load_env, notion_rows, notion_call

ap = argparse.ArgumentParser()
ap.add_argument('--days', type=int, default=2)
ap.add_argument('--apply', action='store_true')
a = ap.parse_args()

env = load_env()
cutoff = str(date.today() - timedelta(days=a.days))
old = [r for r in notion_rows(env) if r['status'] == 'Shortlisted' and r.get('first_seen') and r['first_seen'][:10] < cutoff]
for r in old:
    print(f"{r['first_seen'][:10]}  {r['company']} · {r['title']}")
if not a.apply:
    print(f"\n{len(old)} Shortlisted rows first seen before {cutoff} (dry run; nothing deleted. Re-run with --apply.)")
    raise SystemExit
failed = 0
for r in old:
    res = notion_call('PATCH', f"https://api.notion.com/v1/pages/{r['id']}", env, json={'in_trash': True})
    if res.status_code != 200:
        failed += 1
        print(f"failed: {r['company']} · {r['title']}: {res.status_code} {res.text[:200]}")
print(f"\nmoved {len(old) - failed} rows to the Notion trash" + (f", {failed} failed" if failed else ''))
