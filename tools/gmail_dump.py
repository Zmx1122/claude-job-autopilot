"""Download application-related emails from Gmail into JSON (read-only).

usage: python3 tools/gmail_dump.py [out.json] [--days N | --since YYYY/MM/DD]
default: data/mail/dump.json, last 3 days.
Pulls everything already carrying the label plus unlabeled emails that match job keywords.
Each row: set, msgid, thrid, labels, date, frm, to, subject, body (first 1500 chars).
"""
import email, json, re, sys, os, html
from email.header import decode_header
from datetime import datetime, timedelta
from common import load_env, imap_login, label_name, DATA

args = [a for a in sys.argv[1:]]
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default
out = next((a for a in args if a.endswith('.json')), os.path.join(DATA, 'mail', 'dump.json'))
os.makedirs(os.path.dirname(out), exist_ok=True)
since = opt('--since') or (datetime.now() - timedelta(days=int(opt('--days', 3)))).strftime('%Y/%m/%d')

env = load_env(); label = label_name(env)
M = imap_login(env, readonly=True)
def search(q):
    typ, ids = M.search(None, 'X-GM-RAW', f'"{q}"'); return ids[0].split()
KW = ('(bewerbung OR bewerbungsunterlagen OR application OR applied OR applying OR interview OR vorstellungsgespraech OR absage '
      'OR candidate OR kandidat OR recruiting OR recruiter OR greenhouse OR workday OR personio OR smartrecruiters OR lever OR ashby '
      'OR talent OR hiring OR offer OR vertrag OR contract)')
labeled = search(f'label:{label} after:{since}')
unlabeled = search(f'after:{since} -label:{label} {KW}')
# senders that only produce newsletters / alerts; never application events
SKIP = re.compile(r'grammarly|researchgate|academia-mail|glassdoor|alert|jobleads|jobware|ziprecruiter|newsletter|em\.linkedin|invitations@|'
                  r'notifications-noreply@linkedin|messages-noreply@linkedin|messaging-digest|mailrobot@|no-reply@indeed\.com', re.I)
def dec(s): return ''.join(p.decode(c or 'utf-8', 'replace') if isinstance(p, bytes) else p for p, c in decode_header(s or ''))
def body_text(msg):
    plain, htm = '', ''
    for part in msg.walk():
        ct = part.get_content_type()
        try:
            if ct == 'text/plain' and not plain: plain = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'replace')
            elif ct == 'text/html' and not htm: htm = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'replace')
        except Exception: pass
    t = plain or re.sub(r'<[^>]+>', ' ', re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', htm, flags=re.S | re.I))
    return html.unescape(re.sub(r'\s+', ' ', t)).strip()[:1500]
rows = []
for tag, ids in (('labeled', labeled), ('unlabeled', unlabeled)):
    for i in range(0, len(ids), 25):
        typ, data = M.fetch(b','.join(ids[i:i + 25]).decode(), '(X-GM-MSGID X-GM-THRID X-GM-LABELS BODY.PEEK[])')
        for item in data:
            if not isinstance(item, tuple): continue
            meta = item[0].decode(errors='replace'); msg = email.message_from_bytes(item[1])
            g = lambda k: (re.search(k + r' (\d+)', meta) or [None, None])[1]
            labels = (re.search(r'X-GM-LABELS \((.*?)\)', meta) or [None, ''])[1]
            frm = dec(msg['From'])
            if tag == 'unlabeled' and SKIP.search(frm): continue
            rows.append(dict(set=tag, msgid=g('X-GM-MSGID'), thrid=g('X-GM-THRID'), labels=labels, date=msg['Date'], frm=frm,
                             to=dec(msg['To']), subject=dec(msg['Subject']), body=body_text(msg)))
json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=1)
print(f'since {since}: labeled {len(labeled)}, unlabeled candidates {len(unlabeled)}, kept {len(rows)} -> {out}')
M.logout()
