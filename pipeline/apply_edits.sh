#!/usr/bin/env bash
# Apply all open `lab-edit` GitHub issues to data/labs.json, then commit & push.
# Usage: ./pipeline/apply_edits.sh
set -e
cd "$(dirname "$0")/.."
python3 pipeline/resolve_lab_edit_issues.py
if ! git diff --quiet data/labs.json; then
  git add data/labs.json
  git commit -m "Apply lab edits from issues"
  git push
else
  echo "No changes to labs.json — nothing to commit."
fi
