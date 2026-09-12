#!/usr/bin/env bash
set -euo pipefail

PORT="${ACESTEP_UI_PORT:-8215}"

printf '== Local music preflight ==\n'
printf 'time: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf 'host: %s\n' "$(scutil --get ComputerName 2>/dev/null || hostname)"
printf 'os: %s\n' "$(sw_vers -productVersion 2>/dev/null || uname -sr)"
printf 'arch: %s\n' "$(uname -m)"

if [[ "$(uname)" != "Darwin" ]]; then
  echo 'ERROR: this workflow is prepared for macOS.' >&2
  exit 1
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo 'ERROR: Apple Silicon arm64 is required for the MLX path.' >&2
  exit 1
fi

missing=0
for cmd in git ffmpeg ffprobe shasum lsof; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf 'PASS command %-8s %s\n' "$cmd" "$(command -v "$cmd")"
  else
    printf 'MISS command %s\n' "$cmd"
    missing=1
  fi
done

if command -v uv >/dev/null 2>&1; then
  printf 'PASS uv %s\n' "$(uv --version 2>/dev/null || true)"
else
  echo 'INFO uv is not installed yet; bootstrap_acestep_macos.sh can install it.'
fi

printf '\n== Memory snapshot ==\n'
printf 'physical_bytes: %s\n' "$(sysctl -n hw.memsize 2>/dev/null || echo unknown)"
sysctl vm.swapusage 2>/dev/null || true
memory_pressure -Q 2>/dev/null || true
vm_stat 2>/dev/null | head -n 20 || true

printf '\n== Disk snapshot ==\n'
df -h "$HOME" | tail -n 1 || true

printf '\n== Port check ==\n'
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/tmp/acestep-port-check.$$ 2>/dev/null; then
  cat /tmp/acestep-port-check.$$
  rm -f /tmp/acestep-port-check.$$
  echo "ERROR: port $PORT is already in use. Nothing was stopped." >&2
  exit 2
fi
rm -f /tmp/acestep-port-check.$$
echo "PASS port $PORT is free."

if [[ "$missing" -ne 0 ]]; then
  echo
  echo 'Install missing tools before continuing. Typical Homebrew command:'
  echo '  brew install git ffmpeg'
  exit 3
fi

echo
echo 'PRECHECK_PASS: read-only checks completed. No process or application was stopped.'
