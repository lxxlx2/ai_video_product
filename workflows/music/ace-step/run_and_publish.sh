#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "用法: bash workflows/music/ace-step/run_and_publish.sh <job.json>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
JOB="$1"

if [[ "$JOB" != /* ]]; then
  JOB="$REPO_ROOT/$JOB"
fi

if [[ ! -f "$JOB" ]]; then
  echo "ERROR: job 文件不存在: $JOB" >&2
  exit 3
fi

bash "$SCRIPT_DIR/start_api_macos.sh"

cd "$REPO_ROOT"
python3 "$SCRIPT_DIR/run_job.py" "$JOB"
