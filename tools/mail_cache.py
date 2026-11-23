"""Cache of email classifications by Gmail msgid (data/mail/classification_cache.json — deliberately not a classified_*.json), so an email is classified once.

split_for_classify.py reads it (cached emails skip the LLM); sync_mail.py --apply stores every classified_*.json in it.
Entries are only valid for the classifier prompt they were made with: the file keeps a hash of
.claude/skills/job-mail-sync/classifier_prompt.md, and a different hash means an empty cache.
usage: python3 tools/mail_cache.py            how many emails are cached, and whether the prompt still matches
       python3 tools/mail_cache.py --clear    forget all cached classifications
"""
import glob, hashlib, json, os, sys
from common import ROOT, DATA

PATH = os.path.join(DATA, 'mail', 'classification_cache.json')
PROMPT = os.path.join(ROOT, '.claude', 'skills', 'job-mail-sync', 'classifier_prompt.md')


def prompt_hash():
    return hashlib.sha1(open(PROMPT, 'rb').read()).hexdigest()[:12] if os.path.exists(PROMPT) else ''


def _read():
    try:
        return json.load(open(PATH))
    except (OSError, ValueError):
        return {}


def load():
    """msgid -> classification, or {} when there is no cache or it was made with another classifier prompt."""
    d = _read()
    return d.get('items', {}) if d.get('prompt') == prompt_hash() else {}


def store(mail_dir):
    """Add (or overwrite) every classification in mail_dir/classified_*.json. Returns how many were stored."""
    items = load()
    n = 0
    for f in sorted(glob.glob(os.path.join(mail_dir, 'classified_*.json'))):
        for c in json.load(open(f)):
            if c.get('msgid'):
                items[c['msgid']] = c; n += 1
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    tmp = PATH + '.tmp'
    json.dump({'prompt': prompt_hash(), 'items': items}, open(tmp, 'w'), ensure_ascii=False)
    os.replace(tmp, PATH)
    return n


if __name__ == '__main__':
    if '--clear' in sys.argv:
        if os.path.exists(PATH): os.remove(PATH)
        print('cache cleared')
    else:
        d = _read()
        ok = d.get('prompt') == prompt_hash()
        print(f"{len(d.get('items', {}))} cached classifications in {os.path.relpath(PATH, ROOT)}; "
              f"{'valid' if ok else 'not used (classifier prompt changed or no cache yet)'}")
