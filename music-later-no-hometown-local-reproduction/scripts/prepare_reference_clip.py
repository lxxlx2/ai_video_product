#!/usr/bin/env python3
"""Prepare deterministic short reference clips for ACE-Step experiments.

The source audio stays local. Only lightweight selection metadata is written to Git.
"""

from __future__ import annotations

from array import array
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time


def fail(code: str, message: str, exit_code: int) -> int:
    print(f"ERROR_CODE={code}", file=sys.stderr)
    print(f"ERROR: {message}", file=sys.stderr)
    return exit_code


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def command_output(args: list[str], cwd: Path | None = None) -> str | None:
    try:
        return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def ffprobe_duration(path: Path) -> float:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    data = json.loads(raw)
    return float((data.get("format") or {}).get("duration"))


def decode_proxy(path: Path, sample_rate: int) -> array:
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-",
        ]
    )
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def second_rms_dbfs(samples: array, sample_rate: int) -> list[float]:
    out: list[float] = []
    total = len(samples)
    for start in range(0, total, sample_rate):
        chunk = samples[start : min(start + sample_rate, total)]
        if not chunk:
            continue
        power = sum(float(v) * float(v) for v in chunk) / len(chunk)
        if power <= 0:
            out.append(-96.0)
            continue
        rms = math.sqrt(power) / 32768.0
        out.append(max(-96.0, 20.0 * math.log10(max(rms, 1e-12))))
    return out


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else -96.0


def normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if math.isclose(lo, hi):
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def render_clip(source: Path, target: Path, start: float, duration: float, sample_rate: int, channels: int, codec: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-ac",
            str(channels),
            "-ar",
            str(sample_rate),
            "-c:a",
            codec,
            str(target),
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    args = ap.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return fail("PRECHECK_FAILED", "ffmpeg and ffprobe are required", 2)

    job_path = Path(args.job).expanduser().resolve()
    if not job_path.is_file():
        return fail("PRECHECK_FAILED", f"job file missing: {job_path}", 3)

    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail("PRECHECK_FAILED", f"invalid job JSON: {exc}", 4)

    source = Path(os.path.expanduser(str(job.get("source_audio_path") or ""))).resolve()
    if not source.is_file():
        return fail("SOURCE_MISSING", f"reference audio missing: {source}", 5)

    expected_sha = str(job.get("source_sha256") or "").strip().lower()
    actual_sha = sha256_file(source)
    if expected_sha and actual_sha != expected_sha:
        print(f"expected={expected_sha}", file=sys.stderr)
        print(f"actual={actual_sha}", file=sys.stderr)
        return fail("REFERENCE_INVALID", "reference SHA-256 mismatch", 6)

    task_dir = job_path.parent.parent
    analysis_rel = str(job.get("reference_analysis_path") or "metadata/reference-analysis.latest.json")
    analysis_path = (task_dir / analysis_rel).resolve()
    if not analysis_path.is_file():
        return fail("PRECHECK_FAILED", f"reference analysis missing: {analysis_path}", 7)

    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail("PRECHECK_FAILED", f"invalid reference analysis JSON: {exc}", 8)
    if analysis.get("status") != 1:
        return fail("PRECHECK_FAILED", "reference analysis has not passed", 9)

    policy = job.get("selection_policy") or {}
    clip_duration = float(policy.get("clip_duration_seconds", 32))
    proxy_rate = int(policy.get("analysis_sample_rate", 1000))
    scan_step = float(policy.get("scan_step_seconds", 2))
    edge = float(policy.get("edge_exclusion_seconds", 24))
    candidate_count = int(policy.get("candidate_count", 3))
    separation = float(policy.get("candidate_separation_seconds", 40))
    weights = policy.get("weights") or {}
    w_rise = float(weights.get("transition_rise", 0.45))
    w_activity = float(weights.get("activity", 0.25))
    w_stability = float(weights.get("stability", 0.2))
    w_center = float(weights.get("center_bias", 0.1))

    if not 20 <= clip_duration <= 45:
        return fail("PRECHECK_FAILED", f"clip duration must be 20..45 seconds, got {clip_duration}", 10)
    if proxy_rate < 200 or proxy_rate > 8000:
        return fail("PRECHECK_FAILED", f"analysis sample rate out of range: {proxy_rate}", 11)
    if candidate_count < 1 or candidate_count > 8:
        return fail("PRECHECK_FAILED", f"candidate_count out of range: {candidate_count}", 12)

    try:
        source_duration = ffprobe_duration(source)
    except Exception as exc:
        return fail("REFERENCE_INVALID", f"ffprobe failed: {exc}", 13)
    if source_duration < clip_duration + edge * 2:
        return fail("REFERENCE_INVALID", "reference audio is too short for configured clip policy", 14)

    print("REFERENCE_CLIP_PREPARE_START")
    print(f"source={source}")
    print(f"sha256={actual_sha}")
    print(f"duration={source_duration:.3f}")
    print(f"policy={policy.get('name', 'energy_transition_v1')}")

    try:
        samples = decode_proxy(source, proxy_rate)
    except Exception as exc:
        return fail("REFERENCE_INVALID", f"ffmpeg proxy decode failed: {exc}", 15)

    per_second = second_rms_dbfs(samples, proxy_rate)
    if len(per_second) < int(source_duration) - 3:
        return fail("REFERENCE_INVALID", "decoded proxy duration is unexpectedly short", 16)

    global_median = statistics.median(per_second)
    raw_candidates: list[dict] = []
    start = edge
    latest_start = source_duration - edge - clip_duration
    while start <= latest_start + 1e-9:
        a = max(0, int(math.floor(start)))
        b = min(len(per_second), int(math.ceil(start + clip_duration)))
        window = per_second[a:b]
        if len(window) >= max(8, int(clip_duration * 0.8)):
            third = max(1, len(window) // 3)
            first = window[:third]
            last = window[-third:]
            rise = mean(last) - mean(first)
            activity = sum(1 for v in window if v >= global_median) / len(window)
            stability = -statistics.pstdev(window) if len(window) > 1 else 0.0
            center = start + clip_duration / 2.0
            center_bias = 1.0 - min(1.0, abs(center - source_duration / 2.0) / (source_duration / 2.0))
            raw_candidates.append(
                {
                    "start_seconds": round(start, 3),
                    "duration_seconds": round(clip_duration, 3),
                    "mean_dbfs": round(mean(window), 4),
                    "transition_rise_db": round(rise, 4),
                    "activity_ratio": round(activity, 6),
                    "stability_raw": round(stability, 4),
                    "center_bias": round(center_bias, 6),
                }
            )
        start += scan_step

    if not raw_candidates:
        return fail("RESULT_INVALID", "no clip candidates were produced", 17)

    rise_norm = normalize([float(c["transition_rise_db"]) for c in raw_candidates])
    activity_norm = normalize([float(c["activity_ratio"]) for c in raw_candidates])
    stability_norm = normalize([float(c["stability_raw"]) for c in raw_candidates])
    center_norm = normalize([float(c["center_bias"]) for c in raw_candidates])

    for i, candidate in enumerate(raw_candidates):
        score = (
            w_rise * rise_norm[i]
            + w_activity * activity_norm[i]
            + w_stability * stability_norm[i]
            + w_center * center_norm[i]
        )
        candidate["score"] = round(score, 8)

    ranked = sorted(raw_candidates, key=lambda x: (x["score"], x["transition_rise_db"], x["mean_dbfs"]), reverse=True)
    selected: list[dict] = []
    for candidate in ranked:
        center = float(candidate["start_seconds"]) + clip_duration / 2.0
        if all(abs(center - (float(prev["start_seconds"]) + clip_duration / 2.0)) >= separation for prev in selected):
            selected.append(candidate)
            if len(selected) >= candidate_count:
                break
    if len(selected) < candidate_count:
        for candidate in ranked:
            if candidate in selected:
                continue
            selected.append(candidate)
            if len(selected) >= candidate_count:
                break

    output_cfg = job.get("output") or {}
    output_dir = Path(os.path.expanduser(str(job.get("output_dir") or "~/AI/private/music-source/later-no-hometown/clips"))).resolve()
    sample_rate = int(output_cfg.get("sample_rate", 48000))
    channels = int(output_cfg.get("channels", 2))
    codec = str(output_cfg.get("pcm_codec") or "pcm_s16le")
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered: list[dict] = []
    for index, candidate in enumerate(selected, start=1):
        target = output_dir / f"reference-candidate-{index:02d}.wav"
        try:
            render_clip(source, target, float(candidate["start_seconds"]), clip_duration, sample_rate, channels, codec)
            actual_duration = ffprobe_duration(target)
        except Exception as exc:
            return fail("MEDIA_VALIDATE_FAILED", f"failed to render candidate {index}: {exc}", 18)
        if not 20 <= actual_duration <= 45.5:
            return fail("MEDIA_VALIDATE_FAILED", f"candidate {index} duration invalid: {actual_duration}", 19)
        item = dict(candidate)
        item.update(
            {
                "rank": index,
                "path": str(target),
                "sha256": sha256_file(target),
                "rendered_duration_seconds": round(actual_duration, 6),
            }
        )
        rendered.append(item)

    selected_clip = rendered[0]
    repo_root_text = command_output(["git", "-C", str(task_dir), "rev-parse", "--show-toplevel"])
    repo_root = Path(repo_root_text) if repo_root_text else None
    git_commit = command_output(["git", "rev-parse", "HEAD"], cwd=repo_root) if repo_root else None

    analysis_summary = analysis.get("summary") or {}
    payload = {
        "clip_schema_version": 1,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "job": {
            "path": str(job_path),
            "sha256": sha256_file(job_path),
            "git_commit": git_commit,
        },
        "source": {
            "path": str(source),
            "sha256": actual_sha,
            "duration_seconds": round(source_duration, 6),
        },
        "reference_analysis": {
            "path": str(analysis_path),
            "sha256": sha256_file(analysis_path),
            "task_id": analysis.get("task_id"),
            "bpm": analysis_summary.get("bpm"),
            "keyscale": analysis_summary.get("keyscale"),
            "timesignature": analysis_summary.get("timesignature"),
            "genre": analysis_summary.get("genre"),
        },
        "selection_policy": policy,
        "selection_notes": [
            "Ranking is a deterministic technical heuristic, not a music-quality judgment.",
            "The score favors windows with rising energy, sustained activity, stable level and reasonable song-center proximity.",
            "User listening remains the quality gate before a full-song generation run.",
        ],
        "proxy": {
            "sample_rate": proxy_rate,
            "seconds_analyzed": len(per_second),
            "global_median_dbfs": round(global_median, 4),
        },
        "candidates": rendered,
        "selected": selected_clip,
    }

    out = task_dir / "metadata" / "reference-clip.latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("REFERENCE_CLIP_PREPARE_PASS")
    print(f"metadata={out}")
    print(f"selected_path={selected_clip['path']}")
    print(f"selected_sha256={selected_clip['sha256']}")
    print(f"selected_start={selected_clip['start_seconds']}")
    print(f"selected_duration={selected_clip['rendered_duration_seconds']}")
    print(f"selected_score={selected_clip['score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
