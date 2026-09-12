#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$TASK_DIR" rev-parse --show-toplevel)"
BRANCH="feat/local-music-reproduction-v01"
JOB_FILE="$TASK_DIR/jobs/reference-analysis.json"

CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "ERROR: expected branch $BRANCH, current branch is $CURRENT_BRANCH"
  exit 2
fi

git -C "$REPO_ROOT" fetch origin "$BRANCH" --quiet
LOCAL_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
REMOTE_SHA="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "ERROR: local branch is not synchronized with origin/$BRANCH"
  echo "Run: git pull --ff-only origin $BRANCH"
  exit 3
fi

bash "$SCRIPT_DIR/start_music_api_macos.sh"
python3 "$SCRIPT_DIR/reference_analysis.py" "$JOB_FILE"

REL1="music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.json"
REL2="music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.log"

git -C "$REPO_ROOT" add -- "$REL1" "$REL2"
if git -C "$REPO_ROOT" diff --cached --quiet -- "$REL1" "$REL2"; then
  echo "No analysis changes to commit."
else
  git -C "$REPO_ROOT" commit --only -m "analysis(music): refresh reference analysis" -- "$REL1" "$REL2"
  git -C "$REPO_ROOT" push origin "$BRANCH"
fi

echo
 echo "REFERENCE_ANALYSIS_PUBLISHED"
echo "Tell ChatGPT/Codex the analysis is finished so it can inspect metadata/reference-analysis.latest.json."
