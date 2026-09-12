#!/usr/bin/env bash
set -euo pipefail

PORT="${ACESTEP_API_PORT:-8001}"
STATE_DIR="${ACESTEP_STATE_DIR:-$HOME/AI/run/acestep}"
PID_FILE="$STATE_DIR/api-${PORT}.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "API_NOT_MANAGED no pid file: $PID_FILE"
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$pid" ]]; then
  rm -f "$PID_FILE"
  echo "API_PID_EMPTY"
  exit 0
fi

if ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "API_ALREADY_STOPPED pid=$pid"
  exit 0
fi

cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
if [[ "$cmd" != *"acestep-api"* ]] && [[ "$cmd" != *"acestep.api_server"* ]]; then
  echo "ERROR: PID $pid 当前命令不像 ACE-Step API，拒绝停止。" >&2
  echo "command: $cmd" >&2
  exit 2
fi

kill "$pid"
for _ in $(seq 1 30); do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "API_STOPPED pid=$pid"
    exit 0
  fi
  sleep 1
done

echo "ERROR: API 在 30 秒内没有退出。未发送 SIGKILL，请人工检查 pid=$pid" >&2
exit 3
