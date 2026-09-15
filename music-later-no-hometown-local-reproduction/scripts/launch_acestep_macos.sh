#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-smoke}"
RUNTIME_ROOT="${ACE_RUNTIME_ROOT:-$HOME/AI/runtime/music/acestep-1.5}"
HOST="${ACESTEP_HOST:-127.0.0.1}"
PORT="${ACESTEP_UI_PORT:-8215}"
DOWNLOAD_SOURCE="${ACESTEP_DOWNLOAD_SOURCE:-huggingface}"

case "$PROFILE" in
  smoke)
    DIT="acestep-v15-turbo"
    LM="acestep-5Hz-lm-0.6B"
    ;;
  repro)
    DIT="acestep-v15-xl-turbo"
    LM="acestep-5Hz-lm-1.7B"
    ;;
  quality)
    DIT="acestep-v15-xl-sft"
    LM="acestep-5Hz-lm-4B"
    ;;
  *)
    echo "usage: $0 {smoke|repro|quality}" >&2
    exit 64
    ;;
esac

case "$DOWNLOAD_SOURCE" in
  huggingface|modelscope) ;;
  *)
    echo "ERROR: ACESTEP_DOWNLOAD_SOURCE must be huggingface or modelscope." >&2
    exit 65
    ;;
esac

if [[ "$(uname)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo 'ERROR: MLX launch requires Apple Silicon macOS.' >&2
  exit 1
fi
if [[ ! -d "$RUNTIME_ROOT/.git" ]]; then
  echo "ERROR: ACE-Step checkout missing: $RUNTIME_ROOT" >&2
  echo 'Run bootstrap_acestep_macos.sh first.' >&2
  exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 || { echo 'ERROR: uv not found.' >&2; exit 3; }

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: port $PORT is already in use. Nothing was stopped." >&2
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  exit 4
fi

if [[ "$PROFILE" == "quality" ]]; then
  cat <<'WARN'
WARNING: quality profile is the heaviest profile.
If memory pressure or swap growth becomes unacceptable, stop ACE-Step with Ctrl+C.
WARN
fi

export ACESTEP_LM_BACKEND="mlx"
export TOKENIZERS_PARALLELISM="false"

printf 'profile: %s\n' "$PROFILE"
printf 'DiT:     %s\n' "$DIT"
printf 'LM:      %s\n' "$LM"
printf 'source:  %s\n' "$DOWNLOAD_SOURCE"
printf 'UI:      http://%s:%s\n' "$HOST" "$PORT"
printf 'mode:    foreground; Ctrl+C stops only this ACE-Step process\n\n'

cd "$RUNTIME_ROOT"
exec uv run acestep \
  --port "$PORT" \
  --server-name "$HOST" \
  --language zh \
  --config_path "$DIT" \
  --lm_model_path "$LM" \
  --backend mlx \
  --download-source "$DOWNLOAD_SOURCE" \
  --init_service true \
  --batch_size 1
