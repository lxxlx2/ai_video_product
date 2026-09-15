#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$TASK_DIR" rev-parse --show-toplevel)"
BRANCH="feat/local-music-reproduction-v01"
OUT="$TASK_DIR/metadata/reference-analysis.latest.json"
REL_JSON="music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.json"
REL_LOG="music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.log"
EXPECTED_SHA="288edd5197a7535d9dadfac27dc1aea469999e16dc6dfeaf1291cc882afd6775"
MODE="${1:-run}"

if [[ "$MODE" != "run" && "$MODE" != "publish-only" ]]; then
  printf 'Usage: bash %s [run|publish-only]\n' "$0" >&2
  exit 64
fi

if [[ "$MODE" == "publish-only" ]]; then
  printf '===== T2 STEP 1: publish existing successful analysis =====\n'
  bash "$SCRIPT_DIR/run_reference_analysis.sh" publish-only
else
  printf '===== T2 STEP 1: run and publish reference analysis =====\n'
  bash "$SCRIPT_DIR/run_reference_analysis.sh"
fi

printf '\n===== T2 STEP 2: validate local analysis artifact =====\n'
python3 - "$OUT" "$EXPECTED_SHA" <<'PY'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
expected_sha = sys.argv[2]
if not path.is_file():
    raise SystemExit(f"missing analysis file: {path}")

data = json.loads(path.read_text(encoding="utf-8"))
if data.get("status") != 1:
    raise SystemExit(f"analysis status is not success: {data.get('status')}")

ref = data.get("reference") or {}
if ref.get("sha256") != expected_sha:
    raise SystemExit(f"reference sha mismatch: {ref.get('sha256')}")

engine = data.get("engine") or {}
if engine.get("dit_model") != "acestep-v15-xl-sft":
    raise SystemExit(f"unexpected DiT: {engine.get('dit_model')}")
if engine.get("lm_model") != "acestep-5Hz-lm-4B":
    raise SystemExit(f"unexpected LM: {engine.get('lm_model')}")

health = data.get("health") or {}
if not health.get("models_initialized") or not health.get("llm_initialized"):
    raise SystemExit("analysis snapshot says models were not ready")

result = data.get("result")
if not isinstance(result, dict):
    raise SystemExit("analysis result is not an object")
if not result.get("audio_codes"):
    raise SystemExit("audio_codes missing")
if not isinstance(result.get("metas"), dict):
    raise SystemExit("metas missing")

summary = data.get("summary") or {}
if not summary.get("audio_codes_present") or not summary.get("metas_present"):
    raise SystemExit("summary does not confirm audio_codes/metas")

transport = data.get("transport") or {}
if transport.get("type") != "multipart/form-data":
    raise SystemExit(f"unexpected transport: {transport}")

print("LOCAL_ANALYSIS_VALID=true")
print("TASK_ID=" + str(data.get("task_id") or "none"))
print("BPM=" + str(summary.get("bpm")))
print("KEYSCALE=" + str(summary.get("keyscale")))
print("TIMESIGNATURE=" + str(summary.get("timesignature")))
print("DURATION=" + str(summary.get("duration")))
print("LANGUAGE=" + str(summary.get("language")))
print("AUDIO_CODES_LENGTH=" + str(summary.get("audio_codes_length")))
print("TRANSPORT=" + str(transport.get("type")))
print("ANALYSIS_JOB_COMMIT=" + str((data.get("job") or {}).get("git_commit") or "unknown"))
print("ACESTEP_COMMIT=" + str(engine.get("git_commit") or "unknown"))
PY

printf '\n===== T2 STEP 3: verify publication reached origin =====\n'
git -C "$REPO_ROOT" fetch origin "$BRANCH" --quiet
LOCAL_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
REMOTE_SHA="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  printf 'ERROR_CODE=GIT_PUSH_FAILED\n' >&2
  printf 'ERROR: local and remote branch tips differ after analysis publication\n' >&2
  printf 'LOCAL_SHA=%s\nREMOTE_SHA=%s\n' "$LOCAL_SHA" "$REMOTE_SHA" >&2
  exit 31
fi

for rel in "$REL_JSON" "$REL_LOG"; do
  if ! git -C "$REPO_ROOT" ls-tree -r --name-only "origin/$BRANCH" -- "$rel" | grep -Fxq "$rel"; then
    printf 'ERROR_CODE=GIT_PUSH_FAILED\n' >&2
    printf 'ERROR: published artifact missing on origin/%s: %s\n' "$BRANCH" "$rel" >&2
    exit 32
  fi
  if ! git -C "$REPO_ROOT" diff --quiet "origin/$BRANCH" -- "$rel"; then
    printf 'ERROR_CODE=GIT_PUSH_FAILED\n' >&2
    printf 'ERROR: local artifact differs from origin/%s: %s\n' "$BRANCH" "$rel" >&2
    exit 33
  fi
done

printf 'REMOTE_ANALYSIS_VERIFIED=true\n'
printf 'REMOTE_LOG_VERIFIED=true\n'
printf 'PUBLISHED_COMMIT=%s\n' "$LOCAL_SHA"
printf '\nT2_REFERENCE_ANALYSIS_ACCEPTANCE_PASS\n'
