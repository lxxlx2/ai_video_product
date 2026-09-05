#!/usr/bin/env python3
"""Create a bounded, private vertical-video candidate from local media.

The tool has no upload or publish capability. Every candidate starts with a
human-approval status of ``pending`` and is written below the private runtime
root with a staging-directory rename.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


SCHEMA_VERSION = "1.0"
PRIVATE_RUNTIME = Path.home() / "AI" / "runtime"
OUTPUT_ROOT = PRIVATE_RUNTIME / "livestream-clips"
EXPECTED_FILES = {
    "vertical.mp4",
    "clip.srt",
    "title.txt",
    "caption.txt",
    "approval.json",
    "manifest.json",
}
HASHED_FILES = EXPECTED_FILES - {"manifest.json"}
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
SRT_TIME_RE = re.compile(
    r"^\s*(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})(?:\s+.*)?$"
)
MAX_SRT_BYTES = 2 * 1024 * 1024
MAX_CLIP_MS = 180_000


class ClipError(RuntimeError):
    """Expected validation or production failure."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text_exclusive(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
    path.chmod(0o600)


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    write_text_exclusive(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def validate_run_id(value: str) -> str:
    if not RUN_ID_RE.fullmatch(value):
        raise ClipError("run id must be 1-64 safe filename characters and start with a letter or digit")
    return value


def validate_text(value: str, label: str, max_chars: int) -> str:
    clean = value.strip()
    if not clean:
        raise ClipError(f"{label} must not be empty")
    if len(clean) > max_chars:
        raise ClipError(f"{label} exceeds {max_chars} characters")
    if "\x00" in clean:
        raise ClipError(f"{label} contains a NUL byte")
    return clean


def parse_milliseconds(value: str, label: str) -> int:
    try:
        seconds = Decimal(value)
    except InvalidOperation as exc:
        raise ClipError(f"{label} must be a decimal number of seconds") from exc
    if not seconds.is_finite() or seconds < 0:
        raise ClipError(f"{label} must be a finite, non-negative number")
    return int((seconds * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


def require_local_file(raw_path: str, label: str, suffixes: set[str]) -> Path:
    if "\x00" in raw_path:
        raise ClipError(f"{label} contains a NUL byte")
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        raise ClipError(f"{label} must be an absolute local path")
    if candidate.is_symlink():
        raise ClipError(f"{label} must not be a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ClipError(f"{label} does not exist") from exc
    if not resolved.is_file() or resolved.stat().st_size <= 0:
        raise ClipError(f"{label} must be a non-empty regular file")
    if resolved.suffix.lower() not in suffixes:
        allowed = ", ".join(sorted(suffixes))
        raise ClipError(f"{label} must use one of these suffixes: {allowed}")
    return resolved


def verify_expected_hash(path: Path, expected: str, label: str) -> str:
    normalized = expected.lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ClipError(f"{label} expected SHA-256 must contain exactly 64 hexadecimal characters")
    actual = sha256_file(path)
    if actual != normalized:
        raise ClipError(f"{label} SHA-256 mismatch; refusing to create output")
    return actual


def srt_timestamp_to_ms(groups: tuple[str, ...]) -> int:
    hours, minutes, seconds, milliseconds = (int(part) for part in groups)
    if minutes > 59 or seconds > 59:
        raise ClipError("SRT timestamp contains an invalid minute or second field")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def ms_to_srt_timestamp(value: int) -> str:
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def trim_srt(source: Path, start_ms: int, end_ms: int) -> str:
    if source.stat().st_size > MAX_SRT_BYTES:
        raise ClipError("SRT exceeds the 2 MiB safety limit")
    try:
        text = source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ClipError("SRT must be UTF-8 encoded") from exc

    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip())
    rendered: list[str] = []
    for block in blocks:
        lines = block.splitlines()
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        match = SRT_TIME_RE.fullmatch(lines[timing_index])
        if not match:
            raise ClipError("SRT contains an unsupported timing line")
        cue_start = srt_timestamp_to_ms(match.groups()[0:4])
        cue_end = srt_timestamp_to_ms(match.groups()[4:8])
        if cue_end <= cue_start:
            raise ClipError("SRT contains a non-positive cue duration")
        if cue_end <= start_ms or cue_start >= end_ms:
            continue
        cue_text = "\n".join(lines[timing_index + 1 :]).strip()
        if not cue_text:
            raise ClipError("SRT contains an empty cue")
        clipped_start = max(cue_start, start_ms) - start_ms
        clipped_end = min(cue_end, end_ms) - start_ms
        rendered.append(
            f"{len(rendered) + 1}\n"
            f"{ms_to_srt_timestamp(clipped_start)} --> {ms_to_srt_timestamp(clipped_end)}\n"
            f"{cue_text}"
        )
    if not rendered:
        raise ClipError("no subtitle cues overlap the selected clip")
    return "\n\n".join(rendered) + "\n"


def find_tool(name: str) -> Path:
    raw = shutil.which(name)
    if not raw:
        raise ClipError(f"required local tool is unavailable: {name}")
    resolved = Path(raw).resolve(strict=True)
    if not resolved.is_file():
        raise ClipError(f"required local tool is not a regular file: {name}")
    return resolved


def run_checked(argv: list[str], timeout_seconds: int = 240) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClipError(f"local command timed out: {Path(argv[0]).name}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "no diagnostic output").strip()[-2000:]
        raise ClipError(f"local command failed: {Path(argv[0]).name}: {detail}") from exc


def probe_media(ffprobe: Path, media: Path) -> dict[str, Any]:
    result = run_checked(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels:stream_tags=language",
            "-of",
            "json",
            str(media),
        ],
        timeout_seconds=30,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ClipError("ffprobe returned invalid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("streams"), list):
        raise ClipError("ffprobe result is missing stream data")
    return payload


def validate_source_probe(probe: dict[str, Any], end_ms: int) -> None:
    try:
        duration_ms = int(
            (Decimal(str(probe["format"]["duration"])) * 1000).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise ClipError("source video has no valid duration") from exc
    if duration_ms + 50 < end_ms:
        raise ClipError("selected clip ends after the source video")
    stream_types = {stream.get("codec_type") for stream in probe["streams"]}
    if "video" not in stream_types or "audio" not in stream_types:
        raise ClipError("source must contain both video and audio streams")


def validate_output_probe(probe: dict[str, Any], expected_duration_ms: int) -> None:
    video_streams = [stream for stream in probe["streams"] if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in probe["streams"] if stream.get("codec_type") == "audio"]
    subtitle_streams = [stream for stream in probe["streams"] if stream.get("codec_type") == "subtitle"]
    if len(video_streams) != 1 or not audio_streams:
        raise ClipError("output does not contain the expected video and audio streams")
    if video_streams[0].get("width") != 1080 or video_streams[0].get("height") != 1920:
        raise ClipError("output is not 1080x1920 portrait video")
    if not any(stream.get("codec_name") == "mov_text" for stream in subtitle_streams):
        raise ClipError("output is missing the mov_text subtitle track")
    try:
        actual_duration_ms = int(
            (Decimal(str(probe["format"]["duration"])) * 1000).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise ClipError("output has no valid duration") from exc
    if abs(actual_duration_ms - expected_duration_ms) > 500:
        raise ClipError("output duration differs from the requested clip by more than 0.5 seconds")


def ensure_output_root() -> Path:
    try:
        runtime = PRIVATE_RUNTIME.resolve(strict=True)
    except OSError as exc:
        raise ClipError(f"private runtime root does not exist: {PRIVATE_RUNTIME}") from exc
    if not runtime.is_dir():
        raise ClipError("private runtime root is not a directory")
    if OUTPUT_ROOT.exists() and OUTPUT_ROOT.is_symlink():
        raise ClipError("livestream output root must not be a symbolic link")
    if not OUTPUT_ROOT.exists():
        if OUTPUT_ROOT.parent.resolve(strict=True) != runtime:
            raise ClipError("livestream output parent escaped the private runtime root")
        OUTPUT_ROOT.mkdir(mode=0o700)
    resolved = OUTPUT_ROOT.resolve(strict=True)
    if resolved.parent != runtime or not resolved.is_dir():
        raise ClipError("livestream output root escaped the private runtime boundary")
    return resolved


def require_artifact_dir(raw_path: str) -> Path:
    root = ensure_output_root()
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute() or candidate.is_symlink():
        raise ClipError("artifact must be an absolute, non-symlink path")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ClipError("artifact directory does not exist") from exc
    if not resolved.is_dir() or resolved.parent != root:
        raise ClipError("artifact must be a direct child of the private livestream output root")
    validate_run_id(resolved.name)
    return resolved


def remove_staging(staging: Path, root: Path) -> None:
    if not staging.exists():
        return
    if staging.is_symlink() or staging.parent.resolve(strict=True) != root:
        raise ClipError("refusing to clean an unsafe staging path")
    if not staging.name.startswith(".staging-"):
        raise ClipError("refusing to clean an unrecognized staging directory")
    shutil.rmtree(staging)


def ffmpeg_command(
    ffmpeg: Path,
    source_video: Path,
    trimmed_srt: Path,
    destination: Path,
    start_ms: int,
    end_ms: int,
) -> list[str]:
    start = format_seconds(start_ms)
    end = format_seconds(end_ms)
    video_filter = (
        f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,split=2[bg0][fg0];"
        "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=36[bg];"
        "[fg0]scale=1080:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p[v];"
        f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a]"
    )
    return [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(source_video),
        "-i",
        str(trimmed_srt),
        "-filter_complex",
        video_filter,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-map",
        "1:s:0",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        "-movflags",
        "+faststart",
        str(destination),
    ]


def artifact_hashes(artifact: Path) -> dict[str, str]:
    return {name: sha256_file(artifact / name) for name in sorted(HASHED_FILES)}


def verify_artifact(artifact: Path, ffprobe: Path | None = None) -> dict[str, Any]:
    entries = list(artifact.iterdir())
    actual_names = {path.name for path in entries}
    if actual_names != EXPECTED_FILES or any(path.is_symlink() or not path.is_file() for path in entries):
        missing = sorted(EXPECTED_FILES - actual_names)
        unexpected = sorted(actual_names - EXPECTED_FILES)
        raise ClipError(f"artifact file set mismatch; missing={missing}, unexpected={unexpected}")
    try:
        manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
        approval = json.loads((artifact / "approval.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ClipError("artifact JSON is invalid") from exc
    expected_hashes = manifest.get("outputs", {}).get("sha256")
    if not isinstance(expected_hashes, dict) or set(expected_hashes) != HASHED_FILES:
        raise ClipError("manifest output hashes are incomplete")
    actual_hashes = artifact_hashes(artifact)
    if actual_hashes != expected_hashes:
        raise ClipError("artifact output hash mismatch")
    if approval.get("status") != "pending" or approval.get("publish_allowed") is not False:
        raise ClipError("artifact approval must remain pending with publishing disabled")
    if approval.get("candidate_sha256") != actual_hashes["vertical.mp4"]:
        raise ClipError("approval record is not bound to the video hash")
    if manifest.get("external_publish", {}).get("implemented") is not False:
        raise ClipError("manifest does not explicitly disable external publishing")
    if manifest.get("external_publish", {}).get("attempted") is not False:
        raise ClipError("manifest reports an external publishing attempt")
    if manifest.get("external_publish", {}).get("approval_required") is not True:
        raise ClipError("manifest does not require human approval")
    duration_ms = manifest.get("clip", {}).get("duration_ms")
    if not isinstance(duration_ms, int) or not 0 < duration_ms <= MAX_CLIP_MS:
        raise ClipError("manifest clip duration is invalid")
    selected_ffprobe = ffprobe or find_tool("ffprobe")
    probe = probe_media(selected_ffprobe, artifact / "vertical.mp4")
    validate_output_probe(probe, duration_ms)
    return {
        "status": "verified",
        "artifact": str(artifact),
        "video_sha256": actual_hashes["vertical.mp4"],
        "duration_seconds": probe["format"]["duration"],
        "streams": [stream.get("codec_type") for stream in probe["streams"]],
        "approval": "pending",
        "publish_allowed": False,
    }


def create_candidate(args: argparse.Namespace) -> dict[str, Any]:
    run_id = validate_run_id(args.run_id)
    title = validate_text(args.title, "title", 120)
    caption = validate_text(args.caption, "caption", 1000)
    start_ms = parse_milliseconds(args.start, "start")
    end_ms = parse_milliseconds(args.end, "end")
    duration_ms = end_ms - start_ms
    if duration_ms <= 0:
        raise ClipError("end must be greater than start")
    if duration_ms > MAX_CLIP_MS:
        raise ClipError("clip duration exceeds the 180-second safety limit")

    source_video = require_local_file(
        args.source_video, "source video", {".mp4", ".mov", ".mkv", ".m4v"}
    )
    source_srt = require_local_file(args.source_srt, "source SRT", {".srt"})
    video_hash = verify_expected_hash(source_video, args.expected_video_sha256, "source video")
    srt_hash = verify_expected_hash(source_srt, args.expected_srt_sha256, "source SRT")
    trimmed_srt_text = trim_srt(source_srt, start_ms, end_ms)

    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")
    source_probe = probe_media(ffprobe, source_video)
    validate_source_probe(source_probe, end_ms)

    root = ensure_output_root()
    final = root / run_id
    if final.exists() or final.is_symlink():
        raise ClipError("run id already exists; refusing to overwrite an artifact")
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=root))
    staging.chmod(0o700)

    try:
        trimmed_srt = staging / "clip.srt"
        title_path = staging / "title.txt"
        caption_path = staging / "caption.txt"
        output_video = staging / "vertical.mp4"
        write_text_exclusive(trimmed_srt, trimmed_srt_text)
        write_text_exclusive(title_path, title + "\n")
        write_text_exclusive(caption_path, caption + "\n")

        command = ffmpeg_command(
            ffmpeg, source_video, trimmed_srt, output_video, start_ms, end_ms
        )
        run_checked(command)
        output_video.chmod(0o600)
        output_probe = probe_media(ffprobe, output_video)
        validate_output_probe(output_probe, duration_ms)
        candidate_hash = sha256_file(output_video)
        created_at = utc_now()

        approval = {
            "schema_version": SCHEMA_VERSION,
            "status": "pending",
            "candidate_sha256": candidate_hash,
            "approved_by": None,
            "approved_at": None,
            "publish_allowed": False,
            "note": "Human approval of this exact video hash is required before any publication.",
        }
        write_json_exclusive(staging / "approval.json", approval)
        hashes = artifact_hashes(staging)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "created_at": created_at,
            "source": {
                "video_path": str(source_video),
                "video_sha256": video_hash,
                "srt_path": str(source_srt),
                "srt_sha256": srt_hash,
                "probe": source_probe,
            },
            "clip": {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": duration_ms,
                "title": title,
                "caption": caption,
            },
            "outputs": {
                "directory": str(final),
                "sha256": hashes,
                "probe": output_probe,
            },
            "production": {
                "ffmpeg": str(ffmpeg),
                "ffprobe": str(ffprobe),
                "ffmpeg_argv": command,
                "canvas": "1080x1920",
                "layout": "blurred portrait background with centered landscape source",
                "subtitle_delivery": ["MP4 mov_text track", "clip.srt sidecar"],
            },
            "integrity": {
                "input_hashes_verified": True,
                "output_probe_verified": True,
                "output_hashes_recorded": True,
                "atomic_staging_rename": True,
            },
            "external_publish": {
                "implemented": False,
                "attempted": False,
                "approval_required": True,
            },
        }
        write_json_exclusive(staging / "manifest.json", manifest)
        staging.rename(final)
    except BaseException:
        remove_staging(staging, root)
        raise

    return verify_artifact(final, ffprobe)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a private vertical-video candidate")
    create.add_argument("--source-video", required=True, help="absolute path to a local video")
    create.add_argument("--source-srt", required=True, help="absolute path to a UTF-8 SRT")
    create.add_argument("--expected-video-sha256", required=True)
    create.add_argument("--expected-srt-sha256", required=True)
    create.add_argument("--start", required=True, help="clip start in decimal seconds")
    create.add_argument("--end", required=True, help="clip end in decimal seconds")
    create.add_argument("--run-id", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--caption", required=True)

    verify = subparsers.add_parser("verify", help="verify an existing private candidate")
    verify.add_argument("--artifact", required=True, help="absolute artifact directory path")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "create":
            result = create_candidate(args)
        else:
            artifact = require_artifact_dir(args.artifact)
            result = verify_artifact(artifact)
    except ClipError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
