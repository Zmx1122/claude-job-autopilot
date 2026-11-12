#!/bin/zsh
# Refresh both dashboards from the Notion database. Layout never changes; only data does.
# Steps 1-3 are scripts. Step 4 (the claude.ai artifact) is done by Claude with the Artifact tool, see .claude/skills/job-dashboard/SKILL.md.
set -e; cd "$(dirname "$0")/.."
python3 tools/dashboard_data.py    # Notion -> data/dashboard/data.json + applications.json
python3 tools/charts_png.py        # -> data/dashboard/pie.png flow.png weekly.png
python3 tools/notion_page.py       # rebuild the "Dashboard" section on your Notion page
grep -q '^BACKUP_DIR=' .env 2>/dev/null && python3 tools/backup.py save -m "weekly backup" || true   # weekly copy of personal data
echo "Next (Claude): upload data/dashboard/applications.json to DASHBOARD_URL as the 'applications' dataset."
