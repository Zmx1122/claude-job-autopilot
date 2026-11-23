"""Split a mail dump into chunks for LLM classification and write one ready-to-use prompt per chunk.

usage: python3 tools/split_for_classify.py [data/mail/dump.json] [--size 40] [--no-cache]
Writes data/mail/chunk_N.json and data/mail/prompt_N.md. Claude classifies each chunk (itself, or one subagent per chunk)
and writes data/mail/classified_N.json. The prompt template lives in .claude/skills/job-mail-sync/classifier_prompt.md.
Emails classified on an earlier run (data/mail/classification_cache.json, filled by sync_mail.py --apply) are not classified
again: they go straight to classified_cached.json, which sync_mail.py reads like any other classified_*.json. The daily
3-day window overlaps, so most emails of a daily dump are already in the cache. The cache is ignored when the classifier
prompt has changed since it was written, and with --no-cache.
"""
import json, os, sys
from common import ROOT, DATA, load_profile
from mail_cache import load as load_cache

args = sys.argv[1:]
src = next((a for a in args if a.endswith('.json')), os.path.join(DATA, 'mail', 'dump.json'))
size = int(args[args.index('--size') + 1]) if '--size' in args else 40
rows = json.load(open(src))
outdir = os.path.dirname(os.path.abspath(src))
tpl = open(os.path.join(ROOT, '.claude', 'skills', 'job-mail-sync', 'classifier_prompt.md')).read()
cand = (load_profile().get('candidate') or {})
for old in [f for f in os.listdir(outdir) if f.startswith(('chunk_', 'prompt_', 'classified_'))]:
    os.remove(os.path.join(outdir, old))
cache = {} if '--no-cache' in args else load_cache()
cached = [cache[r['msgid']] for r in rows if r['msgid'] in cache]
rows = [r for r in rows if r['msgid'] not in cache]
if cached:
    json.dump(cached, open(os.path.join(outdir, 'classified_cached.json'), 'w'), ensure_ascii=False, indent=1)
n = -1
for n, i in enumerate(range(0, len(rows), size)):
    chunk = [dict(msgid=r['msgid'], thrid=r['thrid'], date=r['date'], from_=r['frm'], subject=r['subject'], body=r['body'],
                  labeled=r['set'] == 'labeled') for r in rows[i:i + size]]
    cp = os.path.join(outdir, f'chunk_{n}.json'); op = os.path.join(outdir, f'classified_{n}.json')
    json.dump(chunk, open(cp, 'w'), ensure_ascii=False, indent=1)
    prompt = (tpl.replace('{NAME}', cand.get('full_name', 'the candidate')).replace('{EMAIL}', cand.get('email', ''))
                 .replace('{INPUT}', cp).replace('{OUTPUT}', op))
    open(os.path.join(outdir, f'prompt_{n}.md'), 'w').write(prompt)
print(f'{len(cached)} emails classified before (cache) -> classified_cached.json; '
      f'{len(rows)} to classify -> {n + 1} chunks in {outdir}' + ('' if rows else ' (nothing to classify: go straight to sync_mail.py)'))
