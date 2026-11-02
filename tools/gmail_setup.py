"""Check the Gmail connection and the application label.

usage: python3 tools/gmail_setup.py            # check only
       python3 tools/gmail_setup.py --create   # create the label if it does not exist
The label name comes from GMAIL_LABEL in .env (default "applications").
"""
import sys, imaplib
from common import load_env, label_name


def main():
    env = load_env(); label = label_name(env)
    try:
        M = imaplib.IMAP4_SSL(env.get('IMAP_HOST', 'imap.gmail.com'), int(env.get('IMAP_PORT', 993)))
        M.login(env['IMAP_USER'], env['IMAP_APP_PASSWORD'].replace(' ', ''))
    except imaplib.IMAP4.error as e:
        raise SystemExit(f'Gmail login failed: {e}. Check IMAP_USER and IMAP_APP_PASSWORD (16-letter app password, 2-step verification must be on).')
    typ, boxes = M.list()
    names = []
    for b in boxes or []:
        line = b.decode(errors='replace')
        names.append(line.split(' "/" ')[-1].strip('"'))
    print('login ok:', env['IMAP_USER'])
    if label in names:
        print(f'label "{label}" exists')
    elif '--create' in sys.argv:
        typ, resp = M.create(f'"{label}"')
        print(f'label "{label}" created' if typ == 'OK' else f'could not create label: {resp}')
    else:
        print(f'label "{label}" is missing. Run again with --create, or create it in Gmail: left sidebar → Labels → + → "{label}".')
        similar = [n for n in names if label.lower()[:5] in n.lower() or 'bewerb' in n.lower() or 'job' in n.lower()]
        if similar:
            print('existing labels that look related (you can set GMAIL_LABEL to one of them):', similar)
    M.logout()


if __name__ == '__main__':
    main()
