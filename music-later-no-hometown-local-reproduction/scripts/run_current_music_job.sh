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

# 允许存在与本任务无关的本地脏文件，但要求当前分支代码与远端一致。
git -C "$REPO_ROOT" fetch origin "$EXPECTED_BRANCH" --quiet
LOCAL_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
REMOTE_SHA="$(git -C "$REPO_ROOT" rev-parse "origin/$EXPECTED_BRANCH")"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "ERROR: local branch is not synchronized with origin/$EXPECTED_BRANCH"
  echo "Run: git pull --ff-only origin $EXPECTED_BRANCH"
  exit 3
fi

bash "$SCRIPT_DIR/start_music_api_macos.sh"

set +e
python3 "$SCRIPT_DIR/music_job.py" "$JOB_FILE"
JOB_RC=$?
set -e

REVIEW_DIR="$TASK_DIR/review/latest"
if [[ ! -f "$REVIEW_DIR/run.json" ]]; then
  echo "ERROR: music_job.py exited with code $JOB_RC and no review/run.json was produced."
  exit "$JOB_RC"
fi

RUN_ID="$(python3 - "$REVIEW_DIR/run.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding='utf-8'))['run_id'])
PY
)"

STATUS="$(python3 - "$REVIEW_DIR/run.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding='utf-8')).get('status', 'unknown'))
PY
)"

REL_REVIEW="$(python3 - "$REPO_ROOT" "$REVIEW_DIR" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[2]).resolve().relative_to(Path(sys.argv[1]).resolve()))
PY
)"

echo
echo "===== REVIEW SNAPSHOT ====="
echo "run_id: $RUN_ID"
echo "status: $STATUS"
echo "path:   $REL_REVIEW"

git -C "$REPO_ROOT" add -- "$REL_REVIEW"

if git -C "$REPO_ROOT" diff --cached --quiet -- "$REL_REVIEW"; then
  echo "No review changes to commit."
else
  git -C "$REPO_ROOT" commit --only -m "review(music): $RUN_ID $STATUS" -- "$REL_REVIEW"
  git -C "$REPO_ROOT" push origin "$EXPECTED_BRANCH"
fi

echo
echo "MUSIC_REVIEW_PUBLISHED"
echo "branch: $EXPECTED_BRANCH"
echo "run_id:  $RUN_ID"
echo "status:  $STATUS"
echo "review:  $REL_REVIEW"
echo
echo "Next: tell ChatGPT/Codex that the run is finished so it can inspect review/latest from Git."

if [[ "$JOB_RC" -ne 0 ]]; then
  echo "Generation/collection failed with exit code $JOB_RC, but the available review logs were published."
  exit "$JOB_RC"
fi
