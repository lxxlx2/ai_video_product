#!/usr/bin/env bash
set -euo pipefail

EXPECTED_SOURCE_SHA256="176c81b30cbd68de6cd7c900d1513160f9a6a591eb7e9bed65d848f273c48b0e"
PRIVATE_ROOT="${MUSIC_PRIVATE_ROOT:-$HOME/AI/private/music-source/later-no-hometown}"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /absolute/path/to/后来没有故乡.m4a" >&2
  exit 64
fi

SRC="$1"
if [[ ! -f "$SRC" ]]; then
  echo "ERROR: source file not found: $SRC" >&2
  exit 1
fi

for cmd in shasum ffmpeg ffprobe; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $cmd" >&2
    exit 2
  }
done

ACTUAL_SOURCE_SHA256="$(shasum -a 256 "$SRC" | awk '{print $1}')"
if [[ "$ACTUAL_SOURCE_SHA256" != "$EXPECTED_SOURCE_SHA256" ]]; then
  echo 'ERROR: source reference SHA-256 does not match the approved M4A.' >&2
  echo "expected: $EXPECTED_SOURCE_SHA256" >&2
  echo "actual:   $ACTUAL_SOURCE_SHA256" >&2
  exit 3
fi

mkdir -p "$PRIVATE_ROOT"
LOCAL_M4A="$PRIVATE_ROOT/后来没有故乡.m4a"
LOCAL_WAV="$PRIVATE_ROOT/后来没有故乡.reference-48k.wav"
META_JSON="$PRIVATE_ROOT/后来没有故乡.ffprobe.json"
SOURCE_SHA_FILE="$PRIVATE_ROOT/后来没有故乡.source.sha256"
WAV_SHA_FILE="$PRIVATE_ROOT/后来没有故乡.reference-48k.sha256"

cp -p "$SRC" "$LOCAL_M4A"
printf '%s  %s\n' "$EXPECTED_SOURCE_SHA256" "$(basename "$LOCAL_M4A")" > "$SOURCE_SHA_FILE"
ffprobe -v error -show_entries format=duration,format_name,bit_rate -show_entries stream=index,codec_name,codec_type,sample_rate,channels,channel_layout,bit_rate -of json "$LOCAL_M4A" > "$META_JSON"
ffmpeg -hide_banner -loglevel warning -y -i "$LOCAL_M4A" -map 0:a:0 -vn -ar 48000 -ac 2 -c:a pcm_s16le "$LOCAL_WAV"

WORKING_WAV_SHA256="$(shasum -a 256 "$LOCAL_WAV" | awk '{print $1}')"
printf '%s  %s\n' "$WORKING_WAV_SHA256" "$(basename "$LOCAL_WAV")" > "$WAV_SHA_FILE"

printf '\nREFERENCE_READY\n'
printf 'source:      %s\n' "$LOCAL_M4A"
printf 'source_sha:  %s\n' "$EXPECTED_SOURCE_SHA256"
printf 'wav:         %s\n' "$LOCAL_WAV"
printf 'wav_sha:     %s\n' "$WORKING_WAV_SHA256"
printf 'meta:        %s\n' "$META_JSON"
printf '\nThe working files remain outside the public Git repository.\n'
