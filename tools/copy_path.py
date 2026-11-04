"""Copy a file's absolute path to the clipboard — the manual upload fallback on any system.

usage: python3 tools/copy_path.py "<file>"
Then, in the open file dialog: paste into the file-name field (Windows: Ctrl+V · macOS: Cmd+Shift+G, then Cmd+V) and press Enter.
"""
import os, subprocess, sys

p = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
if not os.path.isfile(p):
    sys.exit(f'file not found: {p}')
if sys.platform == 'darwin':
    subprocess.run(['pbcopy'], input=p.encode(), check=True)
elif os.name == 'nt':
    subprocess.run(['powershell', '-NoProfile', '-Command', 'Set-Clipboard -Value $input'], input=p.encode('utf-8'), check=True)
else:
    subprocess.run(['xclip', '-selection', 'clipboard'], input=p.encode(), check=True)
print(f'copied to clipboard: {p}')
