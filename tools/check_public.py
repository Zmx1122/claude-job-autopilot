"""Stop personal data from entering the shared repo. Reads YOUR name, email, phone, address, profile links, employers
(from config/profile.yaml and knowledge/career/facts.yaml) and secrets (.env), then scans what git would publish.

usage: python3 tools/check_public.py            scan all tracked files
       python3 tools/check_public.py --staged   scan only lines staged for the next commit (the pre-commit hook)
Install the hook once per clone: git config core.hooksPath .githooks
Exit 1 and a list of file:line hits if anything personal is found.
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET = [re.compile(p) for p in (r'ntn_[A-Za-z0-9]{30,}', r'secret_[A-Za-z0-9]{30,}', r'apify_api_[A-Za-z0-9]{20,}', r'sk-[A-Za-z0-9_-]{20,}')]


def terms():
    import yaml
    out = set()
    p = os.path.join(ROOT, 'config', 'profile.yaml')
    if os.path.exists(p):
        c = (yaml.safe_load(open(p)) or {}).get('candidate') or {}
        for k in ('full_name', 'email', 'street', 'linkedin_url', 'xing_url', 'portfolio_url'):
            v = str(c.get(k) or '').strip()
            if v: out.add(v.lower().replace('https://', '').replace('www.', '').rstrip('/'))
        out |= {w.lower() for w in str(c.get('full_name') or '').split() if len(w) >= 4}
        if c.get('email'): out.add(str(c['email']).split('@')[0].lower())
        digits = re.sub(r'\D', '', str(c.get('phone') or ''))
        if len(digits) >= 8: out.add('PHONE:' + digits[-8:])
    f = os.path.join(ROOT, 'knowledge', 'career', 'facts.yaml')
    if os.path.exists(f):
        for e in (yaml.safe_load(open(f)) or {}).get('entries', []):
            if e.get('type') in ('work', 'working_student', 'internship', 'research'):
                for n in [e.get('org')] + list(e.get('aliases') or []):
                    if n and len(n) >= 5: out.add(n.lower())
    envp = os.path.join(ROOT, '.env')
    if os.path.exists(envp):
        for line in open(envp):
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1); v = v.strip().strip('"\'')
                # only secrets and personal ids/links, not settings such as GMAIL_LABEL or IMAP_HOST
                if re.search(r'TOKEN|PASS|SECRET|KEY|_ID|URL|USER', k) and len(v) >= 8: out.add(v.lower())
    return out


def lines_to_scan(staged):
    if staged:
        diff = subprocess.run(['git', '-C', ROOT, 'diff', '--cached', '-U0', '--no-color'], capture_output=True, text=True).stdout
        cur = None
        for l in diff.splitlines():
            if l.startswith('+++ '): cur = l[6:]
            elif l.startswith('+') and not l.startswith('+++') and cur: yield cur, '?', l[1:]
        return
    files = subprocess.run(['git', '-C', ROOT, 'ls-files'], capture_output=True, text=True).stdout.split('\n')
    for fn in filter(None, files):
        try:
            for i, l in enumerate(open(os.path.join(ROOT, fn), encoding='utf-8', errors='ignore'), 1):
                yield fn, i, l
        except (IsADirectoryError, FileNotFoundError):
            pass


def main():
    T = terms()
    if not T:
        print('no personal profile here — nothing to compare against'); return
    plain = [t for t in T if not t.startswith('PHONE:')]
    phones = [t[6:] for t in T if t.startswith('PHONE:')]
    hits = []
    for fn, ln, line in lines_to_scan('--staged' in sys.argv):
        if fn == 'tools/check_public.py':
            continue
        low = line.lower(); dig = re.sub(r'\D', '', line)
        why = next((t for t in plain if t in low), None) or next(('phone number' for p in phones if p in dig), None) \
            or next(('secret-like token' for r in SECRET if r.search(line)), None)
        if why:
            hits.append(f'{fn}:{ln}: contains {why!r}')
    if hits:
        print('❌ personal data would be published:\n  ' + '\n  '.join(hits[:40]))
        print('Replace it with a neutral example (Jane Doe, ACME GmbH) or keep the file out of git.')
        sys.exit(1)
    print(f'✅ no personal data found ({len(T)} personal terms checked)')


if __name__ == '__main__':
    main()
