#!/bin/zsh
# Refresh the dashboards from the tracker (Notion database or local data/tracker.csv). Layout never changes; only data does.
# Steps 1-4 are scripts. The claude.ai artifact (optional) is done by Claude with the Artifact tool, see .claude/skills/job-dashboard/SKILL.md.
set -e; cd "$(dirname "$0")/.."
python3 tools/dashboard_data.py    # tracker -> data/dashboard/data.json + applications.json
python3 tools/local_dashboard.py   # -> data/dashboard/Job-Dashboard.html (open by double-click; works without Notion)
backend=$(python3 -c "import sys; sys.path.insert(0, 'tools'); from common import load_env, backend; print(backend(load_env()))")
if [[ $backend == notion ]]; then
  python3 tools/charts_png.py      # -> data/dashboard/pie.png flow.png weekly.png
  python3 tools/notion_page.py     # rebuild the "Dashboard" section on your Notion page
  echo "Next (Claude): upload data/dashboard/applications.json to DASHBOARD_URL as the 'applications' dataset."
fi
grep -q '^BACKUP_DIR=' .env 2>/dev/null && python3 tools/backup.py save -m "weekly backup" || true   # weekly copy of personal data
