"""Send ONE approved reply to an email in the application inbox (Gmail SMTP with the same app password as IMAP).

usage: python3 tools/send_reply.py --gm-msgid <X-GM-MSGID from data/mail/dump.json> --body-file reply.txt [--to addr] [--subject "Re: …"] [--yes | --draft]
Without --yes it only prints the complete message that WOULD be sent (dry run). With --yes it sends it.
With --draft it saves the reply in Gmail's Drafts folder (IMAP APPEND, threaded) and sends nothing: the user edits and sends it in Gmail.
Threading: In-Reply-To / References are taken from the original message; recipient = its Reply-To, else From (override with --to).
From: IMAP_USER in .env, display name = candidate.full_name. Gmail keeps the copy in "Sent".
--quote appends the original message below the reply, verbatim (no "> " prefixes). Use it for ATS mails that say
"Bitte fügen Sie Ihre Antwort oberhalb dieser Zeile ein" / "do not delete the CorrespondenceCode" (SAP SuccessFactors):
their system reads the code from the quoted original, and a reply without it is not processed.
Use only after the user approved the exact text (job-mail-sync skill, "Replying to interview invitations").
"""
import argparse, email, html, re, smtplib, sys
from email.message import EmailMessage
from email.header import decode_header, make_header
from email.utils import formataddr, parseaddr, formatdate, make_msgid
from common import load_env, load_profile, imap_login

ap = argparse.ArgumentParser()
ap.add_argument('--gm-msgid', required=True); ap.add_argument('--body-file', required=True)
ap.add_argument('--to'); ap.add_argument('--subject'); ap.add_argument('--yes', action='store_true')
ap.add_argument('--draft', action='store_true'); ap.add_argument('--quote', action='store_true')
a = ap.parse_args()


def full_text(m):
    """Plain text of a message with its line breaks kept (HTML part converted when there is no text/plain part)."""
    plain, htm = '', ''
    for part in m.walk():
        ct = part.get_content_type()
        try:
            if ct == 'text/plain' and not plain: plain = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'replace')
            elif ct == 'text/html' and not htm: htm = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', 'replace')
        except Exception: pass
    if plain: return plain.replace('\r\n', '\n').strip()
    t = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', htm, flags=re.S | re.I)
    t = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|li|h\d)>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    return re.sub(r'\n[ \t]*\n[\s]*', '\n\n', re.sub(r'[ \t]+', ' ', t)).strip()

env = load_env(); M = imap_login(env, readonly=True)
typ, ids = M.search(None, 'X-GM-MSGID', a.gm_msgid)
if not ids[0]:
    sys.exit(f'message {a.gm_msgid} not found')
typ, data = M.fetch(ids[0].split()[0], '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID REFERENCES SUBJECT FROM REPLY-TO)])')
orig = email.message_from_bytes(data[0][1])
dec = lambda v: str(make_header(decode_header(v or '')))
mid, refs = (orig['Message-ID'] or '').strip(), (orig['References'] or '').strip()
to = a.to or parseaddr(orig['Reply-To'] or orig['From'])[1]
subj = ' '.join((a.subject or dec(orig['Subject'])).split())   # folded subjects carry line breaks (SuccessFactors)
if not subj.lower().startswith(('re:', 'aw:')): subj = 'Re: ' + subj
name = (load_profile().get('candidate') or {}).get('full_name') or ''
msg = EmailMessage()
msg['From'] = formataddr((name, env['IMAP_USER'])); msg['To'] = to; msg['Subject'] = subj
msg['Date'] = formatdate(localtime=True); msg['Message-ID'] = make_msgid(domain=env['IMAP_USER'].split('@')[-1])
if mid: msg['In-Reply-To'] = mid; msg['References'] = (refs + ' ' + mid).strip()
body = open(a.body_file, encoding='utf-8').read().strip() + '\n'
if a.quote:
    typ, raw = M.fetch(ids[0].split()[0], '(BODY.PEEK[])')
    full = email.message_from_bytes(raw[0][1])
    body += f"\n\nAm {dec(full['Date'])} schrieb {dec(full['From'])}:\n\n{full_text(full)}\n"
msg.set_content(body)
print(msg.as_string())
if a.draft:
    import imaplib, time
    D = imap_login(env, readonly=False)
    typ, boxes = D.list()
    box = next((b.decode().split(' "/" ')[-1] for b in boxes if b'\\Drafts' in b), '"[Gmail]/Drafts"')
    typ, res = D.append(box, '(\\Draft)', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    D.logout()
    sys.exit(f'\nsaved as draft in {box}: {typ} — nothing sent' if typ == 'OK' else f'draft failed: {typ} {res}')
if not a.yes:
    sys.exit('\n(dry run — nothing sent. Re-run with --yes after the user approved this exact text.)')
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
    s.login(env['IMAP_USER'], env['IMAP_APP_PASSWORD'].replace(' ', ''))
    s.send_message(msg)
print(f'\nsent to {to}')
