#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <run_id> <candidate_sha256>"
  exit 2
fi

RUN_ID="$1"
EXPECTED_SHA="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$TASK_DIR" rev-parse --show-toplevel)"
BRANCH="feat/local-music-reproduction-v01"
LOCAL_RUN="$HOME/AI/private/music-runs/later-no-hometown/$RUN_ID"
RUN_JSON="$LOCAL_RUN/run.json"
FINAL="$TASK_DIR/output/final.wav"
APPROVAL="$TASK_DIR/metadata/final-approval.json"

if [[ ! -f "$RUN_JSON" ]]; then
  echo "ERROR: run.json not found: $RUN_JSON"
  exit 3
fi

readarray -t VALUES < <(python3 - "$RUN_JSON" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding='utf-8'))
print(r.get('status') or '')
print(r.get('candidate_local_path') or '')
print(r.get('candidate_sha256') or '')
PY
)

STATUS="${VALUES[0]}"
CANDIDATE="${VALUES[1]}"
RECORDED_SHA="${VALUES[2]}"

if [[ "$STATUS" != "succeeded" ]]; then
  echo "ERROR: run status is $STATUS"
  exit 4
fi

if [[ -z "$CANDIDATE" || ! -f "$CANDIDATE" ]]; then
  echo "ERROR: candidate file missing: $CANDIDATE"
  exit 5
fi

if [[ "$RECORDED_SHA" != "$EXPECTED_SHA" ]]; then
  echo "ERROR: approval SHA does not match run.json"
  echo "run.json: $RECORDED_SHA"
  echo "approved: $EXPECTED_SHA"
  exit 6
fi

ACTUAL_SHA="$(shasum -a 256 "$CANDIDATE" | awk '{print $1}')"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  echo "ERROR: candidate bytes no longer match approved SHA"
  echo "actual:   $ACTUAL_SHA"
  echo "approved: $EXPECTED_SHA"
  exit 7
fi

mkdir -p "$TASK_DIR/output" "$TASK_DIR/metadata"
cp -f "$CANDIDATE" "$FINAL"
FINAL_SHA="$(shasum -a 256 "$FINAL" | awk '{print $1}')"
if [[ "$FINAL_SHA" != "$EXPECTED_SHA" ]]; then
  echo "ERROR: final copy hash mismatch"
  exit 8
fi

python3 - "$APPROVAL" "$RUN_ID" "$EXPECTED_SHA" "$CANDIDATE" <<'PY'
import json, sys, time
out, run_id, sha, src = sys.argv[1:]
data = {
    "status": "approved-for-publication",
    "run_id": run_id,
    "candidate_sha256": sha,
    "source_local_candidate": src,
    "final_path": "output/final.wav",
    "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}
open(out, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY

REL_FINAL="music-later-no-hometown-local-reproduction/output/final.wav"
REL_APPROVAL="music-later-no-hometown-local-reproduction/metadata/final-approval.json"

git -C "$REPO_ROOT" add -- "$REL_FINAL" "$REL_APPROVAL"
git -C "$REPO_ROOT" commit --only -m "publish(music): approve later-no-hometown $RUN_ID" -- "$REL_FINAL" "$REL_APPROVAL"
git -C "$REPO_ROOT" push origin "$BRANCH"

echo
 echo "FINAL_MUSIC_PUBLISHED"
echo "run_id: $RUN_ID"
echo "sha256: $EXPECTED_SHA"
echo "path:   $REL_FINAL"
echo
echo "Do not delete local candidates yet. First verify the remote Git/LFS object, then run the cleanup phase."
