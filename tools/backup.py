"""Back up your personal data to a normal folder you can see in Finder / Explorer — with version history — and restore it
on a new computer or after re-downloading the repo. The shared repo never contains this data (it is git-ignored).

usage:
  python3 tools/backup.py save [--to FOLDER] [-m "what changed"] [--include-sensitive]
  python3 tools/backup.py status                    what changed since the last backup
  python3 tools/backup.py history                   the last backups (needs git)
  python3 tools/backup.py restore --from FOLDER [--force]
Folder: --to / --from, else BACKUP_DIR in .env, else ~/Documents/Job Autopilot Data (saved to .env on the first save).

Backed up: config/profile.yaml, config/overrides.json, knowledge/ (documents, manifest, PROFILE.md, career/ fact bank,
interviews, CV content), data/applications/ (tailored CVs and letters), data/drafts/, data/applied.csv.
Not backed up: .env (passwords and tokens — keep them in a password manager), caches that can be rebuilt (data/mail,
data/kb, data/dashboard, data/inbox, data/bundles, previews), and documents marked sensitive (passport, residence permit…)
unless --include-sensitive.
"""
import argparse, filecmp, os, shutil, subprocess, sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
DEFAULT = os.path.join(os.path.expanduser('~'), 'Documents', 'Job Autopilot Data')
FILES = ['config/profile.yaml', 'config/overrides.json', 'data/applied.csv']
DIRS = ['knowledge', 'data/applications', 'data/drafts']
SKIP_PARTS = {'.preview', '__pycache__', '.DS_Store'}
TRACKED = {'knowledge/README.md', 'knowledge/manifest.example.yaml', 'knowledge/inbox/.gitkeep', 'knowledge/career/facts.example.yaml'}
README = """# Job Autopilot — your personal data · 你的个人求职数据

This folder is the backup of everything personal the job autopilot knows about you: answers, documents, fact bank,
tailored CVs and cover letters. It is **not** part of the shared GitHub repo. Keep it private.
这个文件夹是求职助手里所有个人数据的备份：问卷答案、证书材料、事实库、定制简历和求职信。它**不**属于共享的 GitHub 仓库，请妥善保管。

- **Restore** (new computer, or after downloading the repo again): open the repo in the Claude desktop app and say
  "restore my data from <this folder>". · **恢复**：在 Claude 桌面端打开 repo，说"从 <这个文件夹> 恢复我的数据"。
- Every backup is a version; Claude can show what changed ("show my backup history").
  每次备份都是一个版本，Claude 可以告诉你改了什么（"看看备份历史"）。
- Not in here: passwords and tokens (`.env`) — keep them in your password manager.
  这里没有密码和 token（`.env`），请存在密码管理器里。
"""


def env_dir():
    p = os.environ.get('JA_ENV_FILE') or os.path.join(ROOT, '.env')
    if os.path.exists(p):
        for line in open(p):
            if line.strip().startswith('BACKUP_DIR='):
                return line.split('=', 1)[1].strip().strip('"\'') or None
    return None


def sensitive_files():
    man = os.path.join(ROOT, 'knowledge', 'manifest.yaml')
    if not os.path.exists(man):
        return set()
    import yaml
    docs = (yaml.safe_load(open(man)) or {}).get('documents', [])
    return {d['file'] for d in docs if d.get('sensitive') and d.get('file')}


def instance_files(include_sensitive=False):
    """Relative paths of all personal files in the repo folder."""
    skip = set() if include_sensitive else sensitive_files()
    out = [f for f in FILES if os.path.isfile(os.path.join(ROOT, f))]
    for d in DIRS:
        for dp, dns, fns in os.walk(os.path.join(ROOT, d)):
            dns[:] = [x for x in dns if x not in SKIP_PARTS]
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), ROOT)
                if fn not in SKIP_PARTS and rel not in TRACKED and rel not in skip:
                    out.append(rel)
    return sorted(out), sorted(skip)


def backup_files(dest):
    out = []
    for dp, dns, fns in os.walk(dest):
        dns[:] = [x for x in dns if x != '.git' and x not in SKIP_PARTS]
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), dest)
            if rel != 'README.md' and fn not in SKIP_PARTS:
                out.append(rel)
    return sorted(out)


def diff(src_root, src, dst_root, dst):
    s, d = set(src), set(dst)
    changed = [f for f in s & d if not filecmp.cmp(os.path.join(src_root, f), os.path.join(dst_root, f), shallow=False)]
    return sorted(s - d), sorted(changed), sorted(d - s)


def git_ok():
    if not shutil.which('git'):
        return False
    if sys.platform == 'darwin' and subprocess.run(['xcode-select', '-p'], capture_output=True).returncode != 0:
        return False   # /usr/bin/git would pop up an installer instead of running
    return True


def git(dest, *args):
    return subprocess.run(['git', '-C', dest, *args], capture_output=True, text=True)


def save(a):
    dest = os.path.abspath(os.path.expanduser(a.to or env_dir() or DEFAULT))
    os.makedirs(dest, exist_ok=True)
    files, skipped = instance_files(a.include_sensitive)
    if not files:
        raise SystemExit('Nothing to back up yet (no profile, knowledge base or applications).')
    added, changed, removed = diff(ROOT, files, dest, backup_files(dest))
    for f in added + changed:
        os.makedirs(os.path.dirname(os.path.join(dest, f)), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, f), os.path.join(dest, f))
    for f in removed:
        os.remove(os.path.join(dest, f))
    open(os.path.join(dest, 'README.md'), 'w').write(README)
    if not env_dir() or a.to:
        from common import set_env_value
        if os.path.exists(os.path.join(ROOT, '.env')) or os.environ.get('JA_ENV_FILE'):
            set_env_value('BACKUP_DIR', dest)
    version = ''
    if git_ok():
        if not os.path.isdir(os.path.join(dest, '.git')):
            git(dest, 'init', '-q')
        git(dest, 'add', '-A')
        msg = a.m or f'backup {datetime.now():%Y-%m-%d %H:%M}'
        r = git(dest, '-c', 'user.name=Job Autopilot', '-c', 'user.email=backup@localhost', 'commit', '-q', '-m', msg)
        version = ' · new version saved' if r.returncode == 0 else ' · no changes since the last version'
    else:
        version = ' · (git not available: files copied, no version history)'
    print(f'backup → {dest}\n{len(files)} files: {len(added)} new, {len(changed)} changed, {len(removed)} removed{version}')
    if skipped:
        print(f'not backed up (sensitive, use --include-sensitive to include): {", ".join(skipped)}')


def status(a):
    dest = os.path.abspath(os.path.expanduser(env_dir() or DEFAULT))
    if not os.path.isdir(dest):
        raise SystemExit(f'No backup yet (expected at {dest}). Run: python3 tools/backup.py save')
    files, _ = instance_files(False)
    added, changed, removed = diff(ROOT, files, dest, backup_files(dest))
    last = git(dest, 'log', '-1', '--format=%cd · %s', '--date=format:%Y-%m-%d %H:%M').stdout.strip() if git_ok() else ''
    print(f'backup folder: {dest}' + (f'\nlast backup: {last}' if last else ''))
    if not (added or changed or removed):
        print('✅ everything is backed up')
    for tag, lst in (('new', added), ('changed', changed), ('deleted here', removed)):
        for f in lst[:20]:
            print(f'  {tag}: {f}')
        if len(lst) > 20: print(f'  … and {len(lst) - 20} more {tag}')


def history(a):
    dest = os.path.abspath(os.path.expanduser(env_dir() or DEFAULT))
    if not git_ok() or not os.path.isdir(os.path.join(dest, '.git')):
        raise SystemExit('No version history (git missing or no backup yet).')
    print(git(dest, 'log', '-15', '--date=format:%Y-%m-%d %H:%M', '--format=%cd  %s', '--shortstat').stdout)


def restore(a):
    src = os.path.abspath(os.path.expanduser(a.from_))
    if not os.path.isfile(os.path.join(src, 'README.md')) or not os.path.isdir(os.path.join(src, 'knowledge')) and not os.path.isdir(os.path.join(src, 'config')):
        raise SystemExit(f'{src} does not look like a Job Autopilot backup folder (README.md + knowledge/ or config/ expected).')
    files = backup_files(src)
    conflicts = [f for f in files if os.path.exists(os.path.join(ROOT, f)) and f not in TRACKED
                 and not filecmp.cmp(os.path.join(src, f), os.path.join(ROOT, f), shallow=False)]
    if conflicts and not a.force:
        print('These files exist here and differ from the backup — nothing was restored:')
        for f in conflicts[:30]: print('  ', f)
        raise SystemExit('Check them, then run again with --force to overwrite them with the backup.')
    n = 0
    for f in files:
        if f in TRACKED:
            continue
        os.makedirs(os.path.dirname(os.path.join(ROOT, f)), exist_ok=True)
        shutil.copy2(os.path.join(src, f), os.path.join(ROOT, f)); n += 1
    from common import set_env_value
    if not os.path.exists(os.path.join(ROOT, '.env')) and os.path.exists(os.path.join(ROOT, '.env.example')):
        shutil.copy(os.path.join(ROOT, '.env.example'), os.path.join(ROOT, '.env'))
    set_env_value('BACKUP_DIR', src)
    print(f'restored {n} files from {src}.\nNext: put your Notion token and Gmail app password back into .env '
          '(setup skill steps 3–4), then run python3 tools/check_setup.py')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('save'); p.add_argument('--to'); p.add_argument('-m'); p.add_argument('--include-sensitive', action='store_true')
    sub.add_parser('status'); sub.add_parser('history')
    p = sub.add_parser('restore'); p.add_argument('--from', dest='from_', required=True); p.add_argument('--force', action='store_true')
    a = ap.parse_args()
    {'save': save, 'status': status, 'history': history, 'restore': restore}[a.cmd](a)
