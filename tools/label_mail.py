"""Add the application label (GMAIL_LABEL, default "applications") to emails.

usage: python3 tools/label_mail.py <file.json>
<file.json> is either a list of X-GM-MSGIDs, or apps.json from merge.py (uses each record's unlabeled_msgids),
or the to_label list written by sync_mail.py.
"""
import json, sys
from common import load_env, imap_login, label_name

env = load_env(); label = label_name(env)
data = json.load(open(sys.argv[1]))
if isinstance(data, dict):
    data = data.get('to_label', [])
ids = [m for a in data for m in a.get('unlabeled_msgids', [])] if data and isinstance(data[0], dict) else data
M = imap_login(env, readonly=False)
done = 0
for mid in ids:
    typ, nums = M.search(None, 'X-GM-MSGID', str(mid))
    for n in nums[0].split():
        M.store(n, '+X-GM-LABELS', f'"{label}"'); done += 1
print(f'labeled {done} of {len(ids)} emails with "{label}"')
M.logout()
