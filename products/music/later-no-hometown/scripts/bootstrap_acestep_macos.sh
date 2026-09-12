#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_URL="https://github.com/ACE-Step/ACE-Step-1.5.git"
PINNED_COMMIT="ca1e85fe9430179831e6bc6be790c332190a3866"
RUNTIME_ROOT="${ACE_RUNTIME_ROOT:-$HOME/AI/runtime/music/acestep-1.5}"

if [[ "$(uname)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo 'ERROR: this bootstrap is for Apple Silicon macOS.' >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo 'ERROR: git is required. Install Xcode command line tools or Homebrew git.' >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo '[setup] uv not found; installing from Astral official installer...'
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

mkdir -p "$(dirname "$RUNTIME_ROOT")"

if [[ ! -d "$RUNTIME_ROOT/.git" ]]; then
  echo "[clone] $UPSTREAM_URL -> $RUNTIME_ROOT"
  git clone "$UPSTREAM_URL" "$RUNTIME_ROOT"
else
  echo "[reuse] existing checkout: $RUNTIME_ROOT"
  current_origin="$(git -C "$RUNTIME_ROOT" remote get-url origin 2>/dev/null || true)"
  if [[ "$current_origin" != "$UPSTREAM_URL" && "$current_origin" != "git@github.com:ACE-Step/ACE-Step-1.5.git" ]]; then
    echo "ERROR: existing checkout origin is unexpected: $current_origin" >&2
    exit 2
  fi
fi

git -C "$RUNTIME_ROOT" fetch origin main --tags --prune
if ! git -C "$RUNTIME_ROOT" cat-file -e "${PINNED_COMMIT}^{commit}" 2>/dev/null; then
  git -C "$RUNTIME_ROOT" fetch origin "$PINNED_COMMIT"
fi

git -C "$RUNTIME_ROOT" checkout --detach "$PINNED_COMMIT"

echo '[deps] creating/updating isolated uv environment...'
(
  cd "$RUNTIME_ROOT"
  uv sync
)

mkdir -p "$HOME/AI/private/music-source/later-no-hometown"
mkdir -p "$HOME/AI/runtime/music/output/later-no-hometown"

printf '\nBOOTSTRAP_PASS\n'
printf 'checkout: %s\n' "$RUNTIME_ROOT"
printf 'commit:   %s\n' "$(git -C "$RUNTIME_ROOT" rev-parse HEAD)"
printf 'uv:       %s\n' "$(uv --version)"
printf '\nNo existing local-ai-platform service was restarted or modified.\n'
