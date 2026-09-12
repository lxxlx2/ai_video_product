#!/usr/bin/env bash
set -euo pipefail

RUNTIME="${ACESTEP_RUNTIME:-$HOME/AI/runtime/music/acestep-1.5}"
HOST="${ACESTEP_API_HOST:-127.0.0.1}"
PORT="${ACESTEP_API_PORT:-8001}"
STATE_DIR="${ACESTEP_STATE_DIR:-$HOME/AI/run/acestep}"
LOG_DIR="${ACESTEP_LOG_DIR:-$HOME/AI/logs/acestep}"
PID_FILE="$STATE_DIR/api-${PORT}.pid"
LOG_FILE="$LOG_DIR/api-${PORT}.log"
HEALTH_URL="http://${HOST}:${PORT}/health"

mkdir -p "$STATE_DIR" "$LOG_DIR"

if [[ ! -d "$RUNTIME" ]]; then
  echo "ERROR: ACE-Step runtime 不存在: $RUNTIME" >&2
  exit 1
fi

if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
  echo "API_ALREADY_HEALTHY $HEALTH_URL"
  exit 0
fi

# 当前阶段不自动关闭 Gradio。统一内存下同时加载两套大模型风险较高。
if lsof -nP -iTCP:8215 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: 检测到 Gradio 仍在监听 8215。" >&2
  echo "请在启动 Gradio 的终端按 Ctrl+C，随后重新执行本脚本。" >&2
  exit 2
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "ERROR: PID 文件显示 API 进程仍存在: $old_pid" >&2
    echo "请先执行 workflows/music/ace-step/stop_api_macos.sh" >&2
    exit 3
  fi
  rm -f "$PID_FILE"
fi

cd "$RUNTIME"

export ACESTEP_LM_BACKEND="mlx"
export TOKENIZERS_PARALLELISM="false"
export ACESTEP_DOWNLOAD_SOURCE="${ACESTEP_DOWNLOAD_SOURCE:-modelscope}"

CMD=(uv run acestep-api
  --host "$HOST"
  --port "$PORT"
  --download-source "$ACESTEP_DOWNLOAD_SOURCE"
  --no-init
)

echo "STARTING_ACE_STEP_API"
echo "runtime: $RUNTIME"
echo "url:     http://${HOST}:${PORT}"
echo "log:     $LOG_FILE"

nohup "${CMD[@]}" >"$LOG_FILE" 2>&1 &
pid=$!
echo "$pid" > "$PID_FILE"

# API 使用 --no-init，health 应该较快可用。真正模型在首个 job 中按需加载。
for _ in $(seq 1 120); do
  if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "API_READY pid=$pid url=$HEALTH_URL"
    exit 0
  fi

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "ERROR: ACE-Step API 启动进程提前退出。最后日志：" >&2
    tail -80 "$LOG_FILE" >&2 || true
    rm -f "$PID_FILE"
    exit 4
  fi

  sleep 1
done

echo "ERROR: 120 秒内未通过 health check。最后日志：" >&2
tail -80 "$LOG_FILE" >&2 || true
exit 5
