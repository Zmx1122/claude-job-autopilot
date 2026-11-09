"""Send ONE approved reply to an email in the application inbox (Gmail SMTP with the same app password as IMAP).

usage: python3 tools/send_reply.py --gm-msgid <X-GM-MSGID from data/mail/dump.json> --body-file reply.txt [--to addr] [--subject "Re: …"] [--yes]
Without --yes it only prints the complete message that WOULD be sent (dry run). With --yes it sends it.
Threading: In-Reply-To / References are taken from the original message; recipient = its Reply-To, else From (override with --to).
From: IMAP_USER in .env, display name = candidate.full_name. Gmail keeps the copy in "Sent".
Use only after the user approved the exact text (job-mail-sync skill, "Replying to interview invitations").
"""
import argparse, email, smtplib, sys
from email.message import EmailMessage
from email.header import decode_header, make_header
from email.utils import formataddr, parseaddr, formatdate, make_msgid
from common import load_env, load_profile, imap_login

ap = argparse.ArgumentParser()
ap.add_argument('--gm-msgid', required=True); ap.add_argument('--body-file', required=True)
ap.add_argument('--to'); ap.add_argument('--subject'); ap.add_argument('--yes', action='store_true')
a = ap.parse_args()

env = load_env(); M = imap_login(env, readonly=True)
typ, ids = M.search(None, 'X-GM-MSGID', a.gm_msgid)
if not ids[0]:
    sys.exit(f'message {a.gm_msgid} not found')
typ, data = M.fetch(ids[0].split()[0], '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID REFERENCES SUBJECT FROM REPLY-TO)])')
orig = email.message_from_bytes(data[0][1])
dec = lambda v: str(make_header(decode_header(v or '')))
mid, refs = (orig['Message-ID'] or '').strip(), (orig['References'] or '').strip()
to = a.to or parseaddr(orig['Reply-To'] or orig['From'])[1]
subj = a.subject or dec(orig['Subject']).strip()
if not subj.lower().startswith(('re:', 'aw:')): subj = 'Re: ' + subj
name = (load_profile().get('candidate') or {}).get('full_name') or ''
msg = EmailMessage()
msg['From'] = formataddr((name, env['IMAP_USER'])); msg['To'] = to; msg['Subject'] = subj
msg['Date'] = formatdate(localtime=True); msg['Message-ID'] = make_msgid(domain=env['IMAP_USER'].split('@')[-1])
if mid: msg['In-Reply-To'] = mid; msg['References'] = (refs + ' ' + mid).strip()
msg.set_content(open(a.body_file, encoding='utf-8').read().strip() + '\n')
print(msg.as_string())
if not a.yes:
    sys.exit('\n(dry run — nothing sent. Re-run with --yes after the user approved this exact text.)')
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
    s.login(env['IMAP_USER'], env['IMAP_APP_PASSWORD'].replace(' ', ''))
    s.send_message(msg)
print(f'\nsent to {to}')
