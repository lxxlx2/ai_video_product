#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$TASK_DIR" rev-parse --show-toplevel)"
BRANCH="feat/local-music-reproduction-v01"
JOB_FILE="$TASK_DIR/jobs/reference-analysis.json"
REL1="music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.json"
REL2="music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.log"

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

check_synced_before_analysis() {
  git -C "$REPO_ROOT" fetch origin "$BRANCH" --quiet
  local local_sha
  local remote_sha
  local_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  remote_sha="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
  if [[ "$local_sha" != "$remote_sha" ]]; then
    say_error "REMOTE_OUT_OF_SYNC" "local HEAD must equal origin/$BRANCH before a new analysis"
    printf 'LOCAL_SHA=%s\nREMOTE_SHA=%s\n' "$local_sha" "$remote_sha" >&2
    printf 'If a previous analysis already succeeded and only push failed, run:\n' >&2
    printf '  bash %s publish-only\n' "$0" >&2
    return 1
  fi
}

publish_outputs() {
  if [[ ! -f "$REPO_ROOT/$REL1" || ! -f "$REPO_ROOT/$REL2" ]]; then
    say_error "GIT_COMMIT_FAILED" "analysis outputs are missing; cannot publish"
    return 1
  fi

  # These two exact files are the T2 publication allowlist. Force-add is deliberate:
  # broad *.log ignore rules must never block the stable analysis snapshot.
  git -C "$REPO_ROOT" add -f -- "$REL1" "$REL2"
  if ! git -C "$REPO_ROOT" diff --cached --quiet -- "$REL1" "$REL2"; then
    if ! git -C "$REPO_ROOT" commit --only -m "analysis(music): refresh reference analysis" -- "$REL1" "$REL2"; then
      say_error "GIT_COMMIT_FAILED" "failed to commit reference analysis outputs"
      return 1
    fi
  else
    printf 'ANALYSIS_COMMIT_SKIPPED no_changes=true\n'
  fi

  if ! git -C "$REPO_ROOT" push origin "$BRANCH"; then
    say_error "GIT_PUSH_FAILED" "analysis is complete locally, but Git push failed"
    printf 'Do not rerun the analysis. Retry publication with:\n' >&2
    printf '  bash %s publish-only\n' "$0" >&2
    return 1
  fi

  git -C "$REPO_ROOT" fetch origin "$BRANCH" --quiet
  local local_sha
  local remote_sha
  local_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  remote_sha="$(git -C "$REPO_ROOT" rev-parse "origin/$BRANCH")"
  if [[ "$local_sha" != "$remote_sha" ]]; then
    say_error "GIT_PUSH_FAILED" "push returned but local and remote branch tips differ"
    return 1
  fi

  printf 'REFERENCE_ANALYSIS_PUBLISHED\n'
  printf 'PUBLISHED_COMMIT=%s\n' "$local_sha"
}

check_branch

MODE="${1:-run}"
if [[ "$MODE" == "publish-only" ]]; then
  printf 'REFERENCE_ANALYSIS_PUBLISH_ONLY existing_analysis=true\n'
  publish_outputs
  exit 0
fi

if [[ "$MODE" != "run" ]]; then
  printf 'Usage: bash %s [run|publish-only]\n' "$0" >&2
  exit 64
fi

check_synced_before_analysis

printf '===== T2 SERVICE READY GATE =====\n'
bash "$SCRIPT_DIR/music_api_service.sh" ensure
bash "$SCRIPT_DIR/music_api_service.sh" check-ready

printf '\n===== T2 REFERENCE ANALYSIS =====\n'
set +e
python3 "$SCRIPT_DIR/reference_analysis.py" "$JOB_FILE"
analysis_code=$?
set -e
if [[ "$analysis_code" -ne 0 ]]; then
  printf 'REFERENCE_ANALYSIS_RUN_FAILED exit_code=%s\n' "$analysis_code" >&2
  exit "$analysis_code"
fi

printf '\n===== T2 PUBLISH ANALYSIS SNAPSHOT =====\n'
publish_outputs

printf '\nREFERENCE_ANALYSIS_WORKFLOW_PASS\n'
printf 'Tell ChatGPT/Codex the T2 analysis finished so it can inspect metadata/reference-analysis.latest.json.\n'
