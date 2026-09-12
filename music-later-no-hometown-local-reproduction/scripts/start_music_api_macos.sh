#!/usr/bin/env bash
set -euo pipefail

RUNTIME="${ACESTEP_RUNTIME:-$HOME/AI/runtime/music/acestep-1.5}"
HOST="127.0.0.1"
PORT="${ACESTEP_API_PORT:-8001}"
UI_PORT="8215"
STATE_DIR="$HOME/AI/run/music/acestep-api"
LOG_DIR="$HOME/AI/logs/music"
PID_FILE="$STATE_DIR/pid"
LOG_FILE="$LOG_DIR/acestep-api.log"
DIT_MODEL="acestep-v15-xl-sft"
LM_MODEL="acestep-5Hz-lm-4B"

health_json() {
  curl -fsS --max-time 3 "http://${HOST}:${PORT}/health" 2>/dev/null
}

health_ok() {
  health_json >/dev/null 2>&1
}

models_ready() {
  local body
  body="$(health_json)" || return 1
  python3 -c '
import json, sys
expected_dit, expected_lm = sys.argv[1:3]
try:
    payload = json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
data = payload.get("data") or {}
ok = (
    data.get("models_initialized") is True
    and data.get("llm_initialized") is True
    and data.get("loaded_model") == expected_dit
    and data.get("loaded_lm_model") == expected_lm
)
raise SystemExit(0 if ok else 1)
' "$DIT_MODEL" "$LM_MODEL" <<<"$body"
}

print_health() {
  health_json || true
  echo
}

initialize_running_api() {
  echo "ACE-Step API is reachable but required models are not initialized."
  echo "Initializing DiT=$DIT_MODEL and LM=$LM_MODEL through /v1/init ..."

  local response_file="$STATE_DIR/init-response.json"
  mkdir -p "$STATE_DIR"

  if ! curl -fsS --max-time 900 \
    -X POST "http://${HOST}:${PORT}/v1/init" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${DIT_MODEL}\",\"init_llm\":true,\"lm_model_path\":\"${LM_MODEL}\"}" \
    >"$response_file"; then
    echo "ERROR: /v1/init request failed."
    echo "health:"
    print_health
    echo "server log tail:"
    tail -160 "$LOG_FILE" 2>/dev/null || true
    return 1
  fi

  echo "init response:"
  cat "$response_file"
  echo

  if ! models_ready; then
    echo "ERROR: API answered /v1/init but required models are still not ready."
    echo "health:"
    print_health
    echo "server log tail:"
    tail -160 "$LOG_FILE" 2>/dev/null || true
    return 1
  fi

  return 0
}

if health_ok; then
  if models_ready; then
    echo "MUSIC_API_READY http://${HOST}:${PORT}"
    echo "DiT: $DIT_MODEL"
    echo "LM:  $LM_MODEL"
    echo "log: $LOG_FILE"
    exit 0
  fi

  initialize_running_api
  echo "MUSIC_API_READY http://${HOST}:${PORT}"
  echo "DiT: $DIT_MODEL"
  echo "LM:  $LM_MODEL"
  echo "log: $LOG_FILE"
  exit 0
fi

if lsof -nP -iTCP:"$UI_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: ACE-Step Gradio UI is still listening on port $UI_PORT."
  echo "Stop the current Gradio terminal with Ctrl+C first, then rerun this command."
  exit 2
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: port $PORT is occupied, but ACE-Step /health is not responding."
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  exit 3
fi

if [[ ! -d "$RUNTIME" ]]; then
  echo "ERROR: ACE-Step runtime not found: $RUNTIME"
  exit 4
fi

for path in \
  "$RUNTIME/checkpoints/$DIT_MODEL" \
  "$RUNTIME/checkpoints/$LM_MODEL" \
  "$RUNTIME/checkpoints/Qwen3-Embedding-0.6B" \
  "$RUNTIME/checkpoints/vae"; do
  if [[ ! -e "$path" ]]; then
    echo "ERROR: required model asset missing: $path"
    exit 5
  fi
done

mkdir -p "$STATE_DIR" "$LOG_DIR"

export ACESTEP_LM_BACKEND="mlx"
export ACESTEP_CONFIG_PATH="$DIT_MODEL"
export ACESTEP_LM_MODEL_PATH="$LM_MODEL"
export ACESTEP_INIT_LLM="true"
export ACESTEP_NO_INIT="false"
export ACESTEP_DOWNLOAD_SOURCE="modelscope"
export TOKENIZERS_PARALLELISM="false"

cd "$RUNTIME"

echo "Starting ACE-Step REST API..."
echo "runtime: $RUNTIME"
echo "DiT:     $ACESTEP_CONFIG_PATH"
echo "LM:      $ACESTEP_LM_MODEL_PATH"
echo "backend: $ACESTEP_LM_BACKEND"
echo "eager:   ACESTEP_NO_INIT=false"
echo "listen:  http://${HOST}:${PORT}"
echo "log:     $LOG_FILE"

nohup uv run acestep-api \
  --host "$HOST" \
  --port "$PORT" \
  --init-llm \
  --lm-model-path "$ACESTEP_LM_MODEL_PATH" \
  --download-source modelscope \
  >>"$LOG_FILE" 2>&1 &

PID=$!
printf '%s\n' "$PID" > "$PID_FILE"

echo "pid:     $PID"
echo "Waiting for API and required models ..."

for _ in $(seq 1 600); do
  if models_ready; then
    echo "MUSIC_API_READY http://${HOST}:${PORT}"
    echo "DiT: $DIT_MODEL"
    echo "LM:  $LM_MODEL"
    exit 0
  fi

  if ! kill -0 "$PID" >/dev/null 2>&1; then
    echo "ERROR: ACE-Step API process exited before models became ready."
    tail -160 "$LOG_FILE" || true
    exit 6
  fi

  sleep 1
done

echo "ERROR: ACE-Step API models did not become ready within 600 seconds."
echo "health:"
print_health
tail -160 "$LOG_FILE" || true
exit 7
