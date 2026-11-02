"""Split a mail dump into chunks for LLM classification and write one ready-to-use prompt per chunk.

usage: python3 tools/split_for_classify.py [data/mail/dump.json] [--size 40]
Writes data/mail/chunk_N.json and data/mail/prompt_N.md. Claude classifies each chunk (itself, or one subagent per chunk)
and writes data/mail/classified_N.json. The prompt template lives in .claude/skills/job-mail-sync/classifier_prompt.md.
"""
import json, os, sys
from common import ROOT, DATA, load_profile

args = sys.argv[1:]
src = next((a for a in args if a.endswith('.json')), os.path.join(DATA, 'mail', 'dump.json'))
size = int(args[args.index('--size') + 1]) if '--size' in args else 40
rows = json.load(open(src))
outdir = os.path.dirname(os.path.abspath(src))
tpl = open(os.path.join(ROOT, '.claude', 'skills', 'job-mail-sync', 'classifier_prompt.md')).read()
cand = (load_profile().get('candidate') or {})
for old in [f for f in os.listdir(outdir) if f.startswith(('chunk_', 'prompt_', 'classified_'))]:
    os.remove(os.path.join(outdir, old))
n = 0
for n, i in enumerate(range(0, len(rows), size)):
    chunk = [dict(msgid=r['msgid'], thrid=r['thrid'], date=r['date'], from_=r['frm'], subject=r['subject'], body=r['body'],
                  labeled=r['set'] == 'labeled') for r in rows[i:i + size]]
    cp = os.path.join(outdir, f'chunk_{n}.json'); op = os.path.join(outdir, f'classified_{n}.json')
    json.dump(chunk, open(cp, 'w'), ensure_ascii=False, indent=1)
    prompt = (tpl.replace('{NAME}', cand.get('full_name', 'the candidate')).replace('{EMAIL}', cand.get('email', ''))
                 .replace('{INPUT}', cp).replace('{OUTPUT}', op))
    open(os.path.join(outdir, f'prompt_{n}.md'), 'w').write(prompt)
print(f'{len(rows)} emails -> {n + 1 if rows else 0} chunks in {outdir}')
