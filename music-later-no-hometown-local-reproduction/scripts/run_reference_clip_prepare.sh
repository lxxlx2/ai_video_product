#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$TASK_DIR" rev-parse --show-toplevel)"
BRANCH="feat/local-music-reproduction-v01"
JOB_FILE="$TASK_DIR/jobs/reference-clip.json"
REL="music-later-no-hometown-local-reproduction/metadata/reference-clip.latest.json"

say_error() {
  printf 'ERROR_CODE=%s\n' "$1" >&2
  printf 'ERROR: %s\n' "$2" >&2
}

check_branch() {
  local current
  current="$(git -C "$REPO_ROOT" branch --show-current)"
  if [[ "$current" != "$BRANCH" ]]; then
    say_error "WRONG_BRANCH" "expected branch $BRANCH, current branch is $current"
    return 1
  fi
}

check_synced_before_prepare() {
  git -C "$REPO_ROOT" fetch origin "$BRANCH" --quiet
  local local_sha remote_sha
  local_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  remote_sha="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
  if [[ "$local_sha" != "$remote_sha" ]]; then
    say_error "REMOTE_OUT_OF_SYNC" "local HEAD must equal origin/$BRANCH before preparing a new clip"
    printf 'LOCAL_SHA=%s\nREMOTE_SHA=%s\n' "$local_sha" "$remote_sha" >&2
    printf 'If clip preparation already succeeded and only publication failed, run:\n' >&2
    printf '  bash %s publish-only\n' "$0" >&2
    return 1
  fi
}

publish_output() {
  if [[ ! -f "$REPO_ROOT/$REL" ]]; then
    say_error "GIT_COMMIT_FAILED" "clip metadata is missing; cannot publish"
    return 1
  fi

  git -C "$REPO_ROOT" add -- "$REL"
  if ! git -C "$REPO_ROOT" diff --cached --quiet -- "$REL"; then
    if ! git -C "$REPO_ROOT" commit --only -m "analysis(music): refresh reference clip selection" -- "$REL"; then
      say_error "GIT_COMMIT_FAILED" "failed to commit reference clip metadata"
      return 1
    fi
  else
    printf 'CLIP_COMMIT_SKIPPED no_changes=true\n'
  fi

  if ! git -C "$REPO_ROOT" push origin "$BRANCH"; then
    say_error "GIT_PUSH_FAILED" "clip preparation is complete locally, but Git push failed"
    printf 'Do not rerun clip preparation. Retry publication with:\n' >&2
    printf '  bash %s publish-only\n' "$0" >&2
    return 1
  fi

  git -C "$REPO_ROOT" fetch origin "$BRANCH" --quiet
  local local_sha remote_sha
  local_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  remote_sha="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
  if [[ "$local_sha" != "$remote_sha" ]]; then
    say_error "GIT_PUSH_FAILED" "push returned but local and remote branch tips differ"
    return 1
  fi

  printf 'REFERENCE_CLIP_PUBLISHED\n'
  printf 'PUBLISHED_COMMIT=%s\n' "$local_sha"
}

check_branch
MODE="${1:-run}"

if [[ "$MODE" == "publish-only" ]]; then
  printf 'REFERENCE_CLIP_PUBLISH_ONLY existing_metadata=true\n'
  publish_output
  exit 0
fi

if [[ "$MODE" != "run" ]]; then
  printf 'Usage: bash %s [run|publish-only]\n' "$0" >&2
  exit 64
fi

check_synced_before_prepare

printf '===== T3 REFERENCE CLIP PREPARE =====\n'
python3 "$SCRIPT_DIR/prepare_reference_clip.py" "$JOB_FILE"

printf '\n===== T3 PUBLISH CLIP METADATA =====\n'
publish_output

printf '\nREFERENCE_CLIP_WORKFLOW_PASS\n'
