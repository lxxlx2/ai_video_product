#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE="$SCRIPT_DIR/music_api_service.sh"

on_error() {
  local code=$?
  echo
  echo "T1_SERVICE_ACCEPTANCE_FAIL exit=$code"
  echo "===== STATUS ====="
  bash "$SERVICE" status || true
  echo "===== LOG TAIL ====="
  bash "$SERVICE" logs 160 || true
  exit "$code"
}
trap on_error ERR

echo "===== T1 STEP 1: current status ====="
bash "$SERVICE" status

echo
echo "===== T1 STEP 2: stop ====="
bash "$SERVICE" stop

echo
echo "===== T1 STEP 3: status after stop ====="
STATUS_AFTER_STOP="$(bash "$SERVICE" status)"
printf '%s\n' "$STATUS_AFTER_STOP"
if ! printf '%s\n' "$STATUS_AFTER_STOP" | grep -q '^SERVICE_STATE=DOWN$'; then
  echo "ERROR: service did not reach DOWN after stop" >&2
  exit 31
fi

echo
echo "===== T1 STEP 4: ensure READY from DOWN ====="
bash "$SERVICE" ensure
bash "$SERVICE" check-ready

echo
echo "===== T1 STEP 5: idempotent ensure while READY ====="
ENSURE_SECOND="$(bash "$SERVICE" ensure)"
printf '%s\n' "$ENSURE_SECOND"
if ! printf '%s\n' "$ENSURE_SECOND" | grep -q '^READY_REUSED=true$'; then
  echo "ERROR: second ensure did not report READY_REUSED=true" >&2
  exit 32
fi
bash "$SERVICE" check-ready

echo
echo "===== T1 STEP 6: final status ====="
FINAL_STATUS="$(bash "$SERVICE" status)"
printf '%s\n' "$FINAL_STATUS"
for expected in \
  'SERVICE_STATE=READY' \
  'MODELS_INITIALIZED=true' \
  'LLM_INITIALIZED=true' \
  'LOADED_MODEL=acestep-v15-xl-sft' \
  'LOADED_LM_MODEL=acestep-5Hz-lm-4B'; do
  if ! printf '%s\n' "$FINAL_STATUS" | grep -q "^${expected}$"; then
    echo "ERROR: final status missing: $expected" >&2
    exit 33
  fi
done

echo
echo "T1_SERVICE_ACCEPTANCE_PASS"
