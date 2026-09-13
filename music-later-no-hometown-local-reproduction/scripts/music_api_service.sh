#!/usr/bin/env bash
set -euo pipefail

# ACE-Step REST API service manager for macOS / Apple Silicon.
# Compatible with the macOS system Bash 3.2.

RUNTIME="${ACESTEP_RUNTIME:-$HOME/AI/runtime/music/acestep-1.5}"
HOST="${ACESTEP_API_HOST:-127.0.0.1}"
PORT="${ACESTEP_API_PORT:-8001}"
UI_PORT="${ACESTEP_UI_PORT:-8215}"
DIT_MODEL="${ACESTEP_DIT_MODEL:-acestep-v15-xl-sft}"
LM_MODEL="${ACESTEP_LM_MODEL:-acestep-5Hz-lm-4B}"
READY_TIMEOUT="${ACESTEP_READY_TIMEOUT_SECONDS:-900}"
STATE_DIR="${ACESTEP_STATE_DIR:-$HOME/AI/run/music/acestep-api}"
LOG_DIR="${ACESTEP_LOG_DIR:-$HOME/AI/logs/music}"
PID_FILE="$STATE_DIR/pid"
LOG_FILE="$LOG_DIR/acestep-api.log"
INIT_RESPONSE_FILE="$STATE_DIR/init-response.json"

API_URL="http://${HOST}:${PORT}"

say_error() {
  printf 'ERROR_CODE=%s\n' "$1" >&2
  printf 'ERROR: %s\n' "$2" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    say_error "PRECHECK_FAILED" "missing required command: $1"
    exit 20
  }
}

health_json() {
  curl -sS --max-time 4 "${API_URL}/health" 2>/dev/null
}

port_listener_pid() {
  lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

ui_listener_pid() {
  lsof -nP -tiTCP:"$UI_PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

pid_command() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

looks_like_acestep_process() {
  local pid="$1"
  local command_text
  command_text="$(pid_command "$pid")"
  printf '%s' "$command_text" | grep -Eq 'acestep-api|acestep[.]api_server|acestep/api_server'
}

managed_pid() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" >/dev/null 2>&1; then
      printf '%s\n' "$pid"
      return 0
    fi
  fi
  return 1
}

health_state() {
  local body
  body="$(health_json)" || {
    if [[ -n "$(port_listener_pid)" ]]; then
      printf 'FAILED\n'
    else
      printf 'DOWN\n'
    fi
    return 0
  }

  python3 -c '
import json, sys
expected_dit, expected_lm = sys.argv[1:3]
try:
    payload = json.load(sys.stdin)
except Exception:
    print("FAILED")
    raise SystemExit(0)
data = payload.get("data") or {}
if data.get("service") != "ACE-Step API":
    print("FAILED")
    raise SystemExit(0)
models = data.get("models_initialized") is True
llm = data.get("llm_initialized") is True
dit = data.get("loaded_model")
lm = data.get("loaded_lm_model")
if models and llm and dit == expected_dit and lm == expected_lm:
    print("READY")
elif models or llm:
    print("DEGRADED")
else:
    print("HTTP_READY")
' "$DIT_MODEL" "$LM_MODEL" <<<"$body"
}

print_status() {
  local state
  local listener
  local mpid
  local body
  state="$(health_state)"
  listener="$(port_listener_pid)"
  mpid="$(managed_pid || true)"

  printf 'SERVICE_STATE=%s\n' "$state"
  printf 'API_URL=%s\n' "$API_URL"
  printf 'EXPECTED_DIT=%s\n' "$DIT_MODEL"
  printf 'EXPECTED_LM=%s\n' "$LM_MODEL"
  printf 'LISTENER_PID=%s\n' "${listener:-none}"
  printf 'MANAGED_PID=%s\n' "${mpid:-none}"
  printf 'LOG_FILE=%s\n' "$LOG_FILE"

  body="$(health_json || true)"
  if [[ -n "$body" ]]; then
    python3 -c '
import json, sys
try:
    payload = json.load(sys.stdin)
except Exception:
    print("HEALTH_JSON_VALID=false")
    raise SystemExit(0)
data = payload.get("data") or {}
print("HEALTH_JSON_VALID=true")
print("MODELS_INITIALIZED=" + str(bool(data.get("models_initialized"))).lower())
print("LLM_INITIALIZED=" + str(bool(data.get("llm_initialized"))).lower())
print("LOADED_MODEL=" + str(data.get("loaded_model") or "none"))
print("LOADED_LM_MODEL=" + str(data.get("loaded_lm_model") or "none"))
' <<<"$body"
  else
    printf 'HEALTH_JSON_VALID=false\n'
  fi
}

validate_runtime() {
  require_cmd curl
  require_cmd python3
  require_cmd lsof
  require_cmd ps
  require_cmd uv

  if [[ ! -d "$RUNTIME" ]]; then
    say_error "PRECHECK_FAILED" "ACE-Step runtime not found: $RUNTIME"
    exit 21
  fi

  local path
  for path in \
    "$RUNTIME/checkpoints/$DIT_MODEL" \
    "$RUNTIME/checkpoints/$LM_MODEL" \
    "$RUNTIME/checkpoints/Qwen3-Embedding-0.6B" \
    "$RUNTIME/checkpoints/vae"; do
    if [[ ! -e "$path" ]]; then
      say_error "PRECHECK_FAILED" "required model asset missing: $path"
      exit 22
    fi
  done
}

wait_ready() {
  local deadline
  local state
  local now
  deadline=$(( $(date +%s) + READY_TIMEOUT ))

  while true; do
    state="$(health_state)"
    if [[ "$state" == "READY" ]]; then
      return 0
    fi

    now="$(date +%s)"
    if [[ "$now" -ge "$deadline" ]]; then
      return 1
    fi
    sleep 2
  done
}

initialize_models() {
  mkdir -p "$STATE_DIR" "$LOG_DIR"
  printf 'Initializing ACE-Step models through /v1/init ...\n'
  printf 'DiT=%s\nLM=%s\n' "$DIT_MODEL" "$LM_MODEL"

  local http_code
  http_code="$(curl -sS --max-time "$READY_TIMEOUT" \
    -o "$INIT_RESPONSE_FILE" \
    -w '%{http_code}' \
    -X POST "${API_URL}/v1/init" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${DIT_MODEL}\",\"init_llm\":true,\"lm_model_path\":\"${LM_MODEL}\"}" || true)"

  printf 'INIT_HTTP_CODE=%s\n' "${http_code:-none}"
  if [[ -f "$INIT_RESPONSE_FILE" ]]; then
    printf 'INIT_RESPONSE=' 
    cat "$INIT_RESPONSE_FILE"
    printf '\n'
  fi

  if [[ "$http_code" != "200" ]]; then
    say_error "MODEL_INIT_FAILED" "/v1/init returned HTTP ${http_code:-unknown}"
    tail -120 "$LOG_FILE" 2>/dev/null || true
    return 1
  fi

  if ! wait_ready; then
    say_error "MODEL_NOT_READY" "model initialization returned but READY state was not reached"
    print_status >&2
    tail -160 "$LOG_FILE" 2>/dev/null || true
    return 1
  fi
}

start_process() {
  validate_runtime

  if [[ -n "$(ui_listener_pid)" ]]; then
    say_error "SERVICE_START_FAILED" "Gradio UI is listening on port $UI_PORT; stop it before starting the REST API"
    return 1
  fi

  if [[ -n "$(port_listener_pid)" ]]; then
    say_error "SERVICE_START_FAILED" "port $PORT is occupied and ACE-Step health is unavailable"
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
    return 1
  fi

  mkdir -p "$STATE_DIR" "$LOG_DIR"
  rm -f "$PID_FILE"

  {
    printf '\n===== ACE-Step API start %s =====\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
    printf 'runtime=%s\n' "$RUNTIME"
    printf 'dit=%s\n' "$DIT_MODEL"
    printf 'lm=%s\n' "$LM_MODEL"
    printf 'backend=mlx\n'
  } >>"$LOG_FILE"

  cd "$RUNTIME"
  nohup env \
    ACESTEP_LM_BACKEND="mlx" \
    ACESTEP_CONFIG_PATH="$DIT_MODEL" \
    ACESTEP_LM_MODEL_PATH="$LM_MODEL" \
    ACESTEP_INIT_LLM="true" \
    ACESTEP_NO_INIT="false" \
    ACESTEP_DOWNLOAD_SOURCE="modelscope" \
    TOKENIZERS_PARALLELISM="false" \
    uv run acestep-api \
      --host "$HOST" \
      --port "$PORT" \
      --init-llm \
      --lm-model-path "$LM_MODEL" \
      --download-source modelscope \
      >>"$LOG_FILE" 2>&1 &

  local pid=$!
  printf '%s\n' "$pid" >"$PID_FILE"
  printf 'SERVICE_PROCESS_STARTED pid=%s\n' "$pid"

  local deadline=$(( $(date +%s) + READY_TIMEOUT ))
  local init_attempted=0
  local state

  while true; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      say_error "SERVICE_START_FAILED" "ACE-Step API process exited before READY"
      tail -160 "$LOG_FILE" 2>/dev/null || true
      return 1
    fi

    state="$(health_state)"
    if [[ "$state" == "READY" ]]; then
      printf 'MUSIC_API_READY %s\n' "$API_URL"
      return 0
    fi

    if [[ "$state" == "HTTP_READY" || "$state" == "DEGRADED" ]]; then
      if [[ "$init_attempted" -eq 0 ]]; then
        init_attempted=1
        initialize_models || return 1
        printf 'MUSIC_API_READY %s\n' "$API_URL"
        return 0
      fi
    fi

    if [[ "$(date +%s)" -ge "$deadline" ]]; then
      say_error "MODEL_NOT_READY" "ACE-Step API did not reach READY within ${READY_TIMEOUT}s"
      print_status >&2
      tail -160 "$LOG_FILE" 2>/dev/null || true
      return 1
    fi

    sleep 2
  done
}

ensure_ready() {
  validate_runtime
  local state
  state="$(health_state)"

  case "$state" in
    READY)
      printf 'MUSIC_API_READY %s\n' "$API_URL"
      printf 'READY_REUSED=true\n'
      ;;
    HTTP_READY|DEGRADED)
      initialize_models
      printf 'MUSIC_API_READY %s\n' "$API_URL"
      printf 'READY_REUSED=true\n'
      ;;
    DOWN)
      start_process
      printf 'READY_REUSED=false\n'
      ;;
    FAILED)
      say_error "SERVICE_START_FAILED" "port/service state is inconsistent; refusing to mutate an unknown process"
      print_status >&2
      return 1
      ;;
    *)
      say_error "SERVICE_START_FAILED" "unknown service state: $state"
      return 1
      ;;
  esac
}

stop_service() {
  require_cmd lsof
  require_cmd ps

  local state
  local pid
  local listener
  state="$(health_state)"
  pid="$(managed_pid || true)"
  listener="$(port_listener_pid)"

  if [[ "$state" == "DOWN" && -z "$pid" && -z "$listener" ]]; then
    rm -f "$PID_FILE"
    printf 'MUSIC_API_STOPPED already_down=true\n'
    return 0
  fi

  if [[ -n "$pid" ]]; then
    if looks_like_acestep_process "$pid"; then
      printf 'Stopping managed ACE-Step process pid=%s\n' "$pid"
      kill "$pid" 2>/dev/null || true
    else
      printf 'WARN: pid file points to an unexpected process; ignoring pid=%s\n' "$pid" >&2
    fi
  fi

  local i=0
  while [[ "$i" -lt 30 ]]; do
    listener="$(port_listener_pid)"
    [[ -z "$listener" ]] && break
    sleep 1
    i=$((i + 1))
  done

  listener="$(port_listener_pid)"
  if [[ -n "$listener" ]]; then
    if looks_like_acestep_process "$listener"; then
      printf 'Stopping ACE-Step listener pid=%s\n' "$listener"
      kill "$listener" 2>/dev/null || true
      sleep 2
    else
      say_error "SERVICE_STOP_FAILED" "port $PORT remains occupied by an unrecognized process pid=$listener"
      pid_command "$listener" >&2 || true
      return 1
    fi
  fi

  listener="$(port_listener_pid)"
  if [[ -n "$listener" ]]; then
    if looks_like_acestep_process "$listener"; then
      printf 'Force stopping ACE-Step listener pid=%s\n' "$listener"
      kill -9 "$listener" 2>/dev/null || true
      sleep 1
    fi
  fi

  if [[ -n "$(port_listener_pid)" ]]; then
    say_error "SERVICE_STOP_FAILED" "port $PORT is still listening after stop"
    return 1
  fi

  rm -f "$PID_FILE" "$INIT_RESPONSE_FILE"
  printf 'MUSIC_API_STOPPED already_down=false\n'
}

show_logs() {
  local lines="${2:-120}"
  if [[ ! "$lines" =~ ^[0-9]+$ ]]; then
    lines=120
  fi
  if [[ ! -f "$LOG_FILE" ]]; then
    printf 'No log file: %s\n' "$LOG_FILE"
    return 0
  fi
  tail -n "$lines" "$LOG_FILE"
}

usage() {
  cat <<EOF
Usage: bash $(basename "$0") <command>

Commands:
  status                 Print current HTTP/model/PID state. No mutation.
  check-ready            Exit 0 only when expected DiT + LM are READY.
  ensure                 Idempotently reach READY. Reuse, initialize, or start.
  start                  Alias of ensure.
  stop                   Safely stop the ACE-Step REST API.
  restart                stop, then ensure.
  logs [N]               Show the last N log lines. Default 120.

Expected READY configuration:
  API: $API_URL
  DiT: $DIT_MODEL
  LM:  $LM_MODEL
EOF
}

ACTION="${1:-status}"
case "$ACTION" in
  status)
    require_cmd curl
    require_cmd python3
    require_cmd lsof
    require_cmd ps
    print_status
    ;;
  check-ready)
    require_cmd curl
    require_cmd python3
    require_cmd lsof
    [[ "$(health_state)" == "READY" ]]
    ;;
  ensure|start)
    ensure_ready
    ;;
  stop)
    stop_service
    ;;
  restart)
    stop_service
    ensure_ready
    ;;
  logs)
    show_logs "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 64
    ;;
esac
