#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$TASK_DIR" rev-parse --show-toplevel)"
JOB_FILE="${1:-$TASK_DIR/jobs/current.json}"
EXPECTED_BRANCH="feat/local-music-reproduction-v01"

CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
  echo "ERROR: expected branch $EXPECTED_BRANCH, current branch is $CURRENT_BRANCH"
  exit 2
fi

# Avoid silently running from an old checkout. Unrelated dirty files are allowed.
git -C "$REPO_ROOT" fetch origin "$EXPECTED_BRANCH" --quiet
LOCAL_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
REMOTE_SHA="$(git -C "$REPO_ROOT" rev-parse "origin/$EXPECTED_BRANCH")"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "ERROR: local branch is not synchronized with origin/$EXPECTED_BRANCH"
  echo "Run: git pull --ff-only origin $EXPECTED_BRANCH"
  exit 3
fi

bash "$SCRIPT_DIR/start_music_api_macos.sh"

python3 "$SCRIPT_DIR/music_job.py" "$JOB_FILE"

REVIEW_DIR="$TASK_DIR/review/latest"
if [[ ! -f "$REVIEW_DIR/run.json" || ! -f "$REVIEW_DIR/review.mp3" ]]; then
  echo "ERROR: expected review snapshot is missing"
  exit 4
fi

RUN_ID="$(python3 - <<'PY' "$REVIEW_DIR/run.json"
import json, sys
print(json.load(open(sys.argv[1], encoding='utf-8'))['run_id'])
PY
)"

REL_REVIEW="$(python3 - <<'PY' "$REPO_ROOT" "$REVIEW_DIR"
from pathlib import Path
import sys
print(Path(sys.argv[2]).resolve().relative_to(Path(sys.argv[1]).resolve()))
PY
)"

echo
 echo "===== REVIEW SNAPSHOT ====="
echo "run_id: $RUN_ID"
echo "path:   $REL_REVIEW"

git -C "$REPO_ROOT" add -- "$REL_REVIEW"

if git -C "$REPO_ROOT" diff --cached --quiet -- "$REL_REVIEW"; then
  echo "No review changes to commit."
else
  git -C "$REPO_ROOT" commit --only -m "review(music): $RUN_ID" -- "$REL_REVIEW"
  git -C "$REPO_ROOT" push origin "$EXPECTED_BRANCH"
fi

echo
echo "MUSIC_REVIEW_PUBLISHED"
echo "branch: $EXPECTED_BRANCH"
echo "run_id:  $RUN_ID"
echo "review:  $REL_REVIEW"
echo
echo "Next: tell ChatGPT/Codex that the run is finished so it can inspect review/latest from Git."
