"""One-shot health check of everything the autopilot needs. Prints a checklist; exits 1 if a required item fails.

usage: python3 tools/check_setup.py
"""
import os, sys, subprocess, importlib
from common import ROOT, env_path

ok_all = True
def line(ok, what, hint=''):
    global ok_all
    ok_all &= bool(ok) or ok is None
    mark = '✅' if ok else ('⚠️ ' if ok is None else '❌')
    print(f'{mark} {what}' + (f'\n     → {hint}' if hint and not ok else ''))

# 1. python packages
for mod, pkg in (('requests', 'requests'), ('yaml', 'pyyaml'), ('PIL', 'pillow'), ('pypdf', 'pypdf')):
    try: importlib.import_module(mod); line(True, f'python package {pkg}')
    except ImportError: line(False, f'python package {pkg}', 'python3 -m pip install -r requirements.txt')

# 2. config files
line(os.path.exists(env_path()), '.env exists', 'cp .env.example .env')
prof = os.path.join(ROOT, 'config', 'profile.yaml')
line(os.path.exists(prof), 'config/profile.yaml exists', 'answer the questionnaire (setup skill, step 1)')

env = {}
if os.path.exists(env_path()):
    from common import load_env; env = load_env()
for k in ('NOTION_TOKEN', 'NOTION_PARENT_PAGE_ID', 'NOTION_DATABASE_ID', 'IMAP_USER', 'IMAP_APP_PASSWORD'):
    line(bool(env.get(k)), f'.env has {k}', 'see docs/credentials.md')

# 3. knowledge base files referenced by the profile
if os.path.exists(prof):
    import yaml
    p = yaml.safe_load(open(prof)) or {}
    cvs = (p.get('candidate') or {}).get('cv_variants') or []
    line(bool(cvs), 'profile lists at least one CV', 'put a PDF in knowledge/cv/ and list it under candidate.cv_variants')
    for cv in cvs:
        f = os.path.join(ROOT, cv.get('file', ''))
        line(os.path.exists(f), f"CV file {cv.get('file')}", 'file missing; check the path in config/profile.yaml')
    man = os.path.join(ROOT, 'knowledge', 'manifest.yaml')
    line(os.path.exists(man), 'knowledge/manifest.yaml (index of your documents)', 'put files in knowledge/inbox/ and run the job-knowledge-base skill')
    line(os.path.exists(os.path.join(ROOT, 'knowledge', 'PROFILE.md')), 'knowledge/PROFILE.md (knowledge profile)', 'job-knowledge-base skill, step A6')
    inbox = [f for f in os.listdir(os.path.join(ROOT, 'knowledge', 'inbox')) if not f.startswith('.')] if os.path.isdir(os.path.join(ROOT, 'knowledge', 'inbox')) else []
    line(not inbox or None, 'knowledge/inbox/ is processed', f'{len(inbox)} file(s) waiting: run the job-knowledge-base skill')

    facts = os.path.join(ROOT, 'knowledge', 'career', 'facts.yaml')
    if os.path.exists(facts):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'facts.py'), 'check'], capture_output=True, text=True)
        line(r.returncode == 0, 'knowledge/career/facts.yaml (fact bank for CVs and cover letters)', (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else '')
    else:
        line(None, 'knowledge/career/facts.yaml (fact bank, needed for tailored CVs and cover letters)',
             'no CV → job-career-coach skill; CVs exist → setup skill step 1b')

# 3b. PDF writer for generated CVs / cover letters (optional)
try:
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from doc_render import browser
    line(bool(browser()), 'Chromium browser for writing CV / cover-letter PDFs')
except SystemExit as e:
    line(None, 'Chromium browser for writing CV / cover-letter PDFs (optional)', str(e))

# 4. Notion
if env.get('NOTION_TOKEN') and env.get('NOTION_DATABASE_ID'):
    import requests
    from common import notion_headers
    r = requests.get(f"https://api.notion.com/v1/databases/{env['NOTION_DATABASE_ID']}", headers=notion_headers(env))
    line(r.status_code == 200, 'Notion database reachable', f'HTTP {r.status_code}: share the page with your integration, then run tools/notion_setup.py')

# 5. Gmail
if env.get('IMAP_USER') and env.get('IMAP_APP_PASSWORD'):
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'gmail_setup.py')], capture_output=True, text=True)
    txt = (out.stdout + out.stderr).strip()
    line('login ok' in txt, 'Gmail IMAP login', txt.splitlines()[-1] if txt else '')
    line('exists' in txt or 'created' in txt, f"Gmail label \"{env.get('GMAIL_LABEL', 'applications')}\"", 'python3 tools/gmail_setup.py --create')

# 6. macOS file-upload permission (optional, needed only for company-site uploads)
if sys.platform == 'darwin':
    r = subprocess.run(['osascript', '-e', 'tell application "System Events" to count processes'], capture_output=True, text=True)
    line(r.returncode == 0 or None, 'macOS Accessibility for file uploads (optional)',
         'System Settings → Privacy & Security → Accessibility → turn on "Claude". See docs/macos-permissions.md')

print('\nAll required checks passed.' if ok_all else '\nFix the ❌ items above, then run this check again.')
sys.exit(0 if ok_all else 1)
