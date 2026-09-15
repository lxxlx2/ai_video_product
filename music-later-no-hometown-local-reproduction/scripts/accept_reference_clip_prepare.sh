#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$TASK_DIR" rev-parse --show-toplevel)"
BRANCH="feat/local-music-reproduction-v01"
OUT="$TASK_DIR/metadata/reference-clip.latest.json"
REL="music-later-no-hometown-local-reproduction/metadata/reference-clip.latest.json"
EXPECTED_SOURCE_SHA="288edd5197a7535d9dadfac27dc1aea469999e16dc6dfeaf1291cc882afd6775"
MODE="${1:-run}"

if [[ "$MODE" != "run" && "$MODE" != "publish-only" && "$MODE" != "verify-only" ]]; then
  printf 'Usage: bash %s [run|publish-only|verify-only]\n' "$0" >&2
  exit 64
fi

if [[ "$MODE" == "run" ]]; then
  printf '===== T3 STEP 1: prepare and publish reference clips =====\n'
  bash "$SCRIPT_DIR/run_reference_clip_prepare.sh"
elif [[ "$MODE" == "publish-only" ]]; then
  printf '===== T3 STEP 1: publish existing clip metadata =====\n'
  bash "$SCRIPT_DIR/run_reference_clip_prepare.sh" publish-only
else
  printf '===== T3 STEP 1: skip preparation/publication and verify existing artifacts =====\n'
fi

printf '\n===== T3 STEP 2: validate local clip artifacts =====\n'
python3 - "$OUT" "$EXPECTED_SOURCE_SHA" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
expected_source_sha = sys.argv[2]
if not path.is_file():
    raise SystemExit(f"missing clip metadata: {path}")

data = json.loads(path.read_text(encoding="utf-8"))
source = data.get("source") or {}
if source.get("sha256") != expected_source_sha:
    raise SystemExit(f"source sha mismatch: {source.get('sha256')}")

candidates = data.get("candidates") or []
if len(candidates) < 3:
    raise SystemExit(f"expected at least 3 candidates, got {len(candidates)}")

selected = data.get("selected") or {}
if selected.get("rank") != 1:
    raise SystemExit(f"selected candidate rank must be 1, got {selected.get('rank')}")
selected_path = Path(str(selected.get("path") or "")).expanduser()
if not selected_path.is_file():
    raise SystemExit(f"selected clip missing: {selected_path}")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

actual_sha = sha256_file(selected_path)
if actual_sha != selected.get("sha256"):
    raise SystemExit(f"selected clip sha mismatch: metadata={selected.get('sha256')} actual={actual_sha}")

duration = float(selected.get("rendered_duration_seconds") or 0)
if not 20 <= duration <= 45.5:
    raise SystemExit(f"selected clip duration invalid: {duration}")

for item in candidates:
    p = Path(str(item.get("path") or "")).expanduser()
    if not p.is_file():
        raise SystemExit(f"candidate clip missing: {p}")
    if sha256_file(p) != item.get("sha256"):
        raise SystemExit(f"candidate sha mismatch: {p}")

print("LOCAL_REFERENCE_CLIPS_VALID=true")
print("SELECTED_PATH=" + str(selected_path))
print("SELECTED_SHA256=" + actual_sha)
print("SELECTED_START=" + str(selected.get("start_seconds")))
print("SELECTED_DURATION=" + str(duration))
print("SELECTED_SCORE=" + str(selected.get("score")))
print("REFERENCE_BPM=" + str((data.get("reference_analysis") or {}).get("bpm")))
print("REFERENCE_KEY=" + str((data.get("reference_analysis") or {}).get("keyscale")))
for item in candidates:
    print(
        "CANDIDATE_{rank}=start:{start},duration:{duration},score:{score},path:{path}".format(
            rank=item.get("rank"),
            start=item.get("start_seconds"),
            duration=item.get("rendered_duration_seconds"),
            score=item.get("score"),
            path=item.get("path"),
        )
    )
PY

printf '\n===== T3 STEP 3: verify metadata reached origin =====\n'
git -C "$REPO_ROOT" fetch origin "$BRANCH" --quiet
LOCAL_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
REMOTE_SHA="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  printf 'ERROR_CODE=GIT_PUSH_FAILED\n' >&2
  printf 'ERROR: local and remote branch tips differ after clip publication\n' >&2
  printf 'LOCAL_SHA=%s\nREMOTE_SHA=%s\n' "$LOCAL_SHA" "$REMOTE_SHA" >&2
  exit 31
fi

if ! git -C "$REPO_ROOT" ls-tree -r --name-only "origin/$BRANCH" -- "$REL" | grep -Fxq "$REL"; then
  printf 'ERROR_CODE=GIT_PUSH_FAILED\n' >&2
  printf 'ERROR: clip metadata missing on origin/%s\n' "$BRANCH" >&2
  exit 32
fi
if ! git -C "$REPO_ROOT" diff --quiet "origin/$BRANCH" -- "$REL"; then
  printf 'ERROR_CODE=GIT_PUSH_FAILED\n' >&2
  printf 'ERROR: local clip metadata differs from origin/%s\n' "$BRANCH" >&2
  exit 33
fi

printf 'REMOTE_CLIP_METADATA_VERIFIED=true\n'
printf 'PUBLISHED_COMMIT=%s\n' "$LOCAL_SHA"
printf '\nT3_REFERENCE_CLIP_ACCEPTANCE_PASS\n'
