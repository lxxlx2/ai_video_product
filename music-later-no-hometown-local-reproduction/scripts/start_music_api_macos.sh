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

health_ok() {
  curl -fsS --max-time 2 "http://${HOST}:${PORT}/health" >/dev/null 2>&1
}

if health_ok; then
  echo "MUSIC_API_READY http://${HOST}:${PORT}"
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
  "$RUNTIME/checkpoints/acestep-v15-xl-sft" \
  "$RUNTIME/checkpoints/acestep-5Hz-lm-4B" \
  "$RUNTIME/checkpoints/Qwen3-Embedding-0.6B" \
  "$RUNTIME/checkpoints/vae"; do
  if [[ ! -e "$path" ]]; then
    echo "ERROR: required model asset missing: $path"
    exit 5
  fi
done

mkdir -p "$STATE_DIR" "$LOG_DIR"

export ACESTEP_LM_BACKEND="mlx"
export ACESTEP_CONFIG_PATH="acestep-v15-xl-sft"
export ACESTEP_LM_MODEL_PATH="acestep-5Hz-lm-4B"
export ACESTEP_INIT_LLM="true"
export ACESTEP_DOWNLOAD_SOURCE="modelscope"
export TOKENIZERS_PARALLELISM="false"

cd "$RUNTIME"

echo "Starting ACE-Step REST API..."
echo "runtime: $RUNTIME"
echo "DiT:     $ACESTEP_CONFIG_PATH"
echo "LM:      $ACESTEP_LM_MODEL_PATH"
echo "backend: $ACESTEP_LM_BACKEND"
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
echo "Waiting for /health ..."

for _ in $(seq 1 300); do
  if health_ok; then
    echo "MUSIC_API_READY http://${HOST}:${PORT}"
    exit 0
  fi

  if ! kill -0 "$PID" >/dev/null 2>&1; then
    echo "ERROR: ACE-Step API process exited before becoming healthy."
    tail -120 "$LOG_FILE" || true
    exit 6
  fi

  sleep 1
done

echo "ERROR: ACE-Step API did not become healthy within 300 seconds."
tail -120 "$LOG_FILE" || true
exit 7
