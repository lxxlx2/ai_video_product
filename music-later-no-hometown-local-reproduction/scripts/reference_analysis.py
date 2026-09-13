#!/usr/bin/env python3
"""Run ACE-Step full reference analysis and write a reproducible Git snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

EXPECTED_DIT = "acestep-v15-xl-sft"
EXPECTED_LM = "acestep-5Hz-lm-4B"
DEFAULT_RUNTIME = "~/AI/runtime/music/acestep-1.5"


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


def valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value or ""))


def command_output(args: list[str], cwd: Path | None = None) -> str | None:
    try:
        return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def ffprobe_info(path: Path) -> dict:
    if not shutil.which("ffprobe"):
        return {"available": False, "error": "ffprobe not found"}
    try:
        raw = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration,size,bit_rate:stream=codec_name,codec_type,sample_rate,channels,channel_layout",
                "-of", "json", str(path),
            ],
            text=True,
        )
        payload = json.loads(raw)
        payload["available"] = True
        return payload
    except Exception as exc:
        return {"available": True, "error": str(exc)}


def http_json(url: str, method: str = "GET", payload: dict | None = None, timeout: int = 30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body}") from exc


def normalize_result(item: dict) -> dict:
    raw = item.get("result")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
    else:
        parsed = raw
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        parsed = parsed[0]
    return {"task_id": item.get("task_id"), "status": item.get("status"), "result": parsed}


def result_summary(result: object) -> dict:
    if not isinstance(result, dict):
        return {"valid": False, "result_type": type(result).__name__}
    audio_codes = result.get("audio_codes")
    return {
        "valid": True,
        "status_message": result.get("status_message"),
        "bpm": result.get("bpm"),
        "keyscale": result.get("keyscale"),
        "timesignature": result.get("timesignature"),
        "duration": result.get("duration"),
        "genre": result.get("genre"),
        "language": result.get("language"),
        "prompt": result.get("prompt"),
        "lyrics_present": bool(result.get("lyrics")),
        "metas_present": isinstance(result.get("metas"), dict),
        "audio_codes_present": bool(audio_codes),
        "audio_codes_length": len(audio_codes) if isinstance(audio_codes, str) else None,
        "audio_paths": result.get("audio_paths"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--poll-seconds", type=int, default=5)
    ap.add_argument("--timeout-seconds", type=int, default=3600)
    args = ap.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    if not job_path.is_file():
        return fail("PRECHECK_FAILED", f"job file missing: {job_path}", 2)

    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail("PRECHECK_FAILED", f"invalid job JSON: {exc}", 3)

    base_url = job.get("api", {}).get("base_url", "http://127.0.0.1:8001").rstrip("/")
    request_body = dict(job.get("request", {}))
    src_value = str(request_body.get("src_audio_path") or "").strip()
    if not src_value:
        return fail("SOURCE_MISSING", "src_audio_path is empty", 4)

    src = Path(os.path.expanduser(src_value)).resolve()
    if not src.is_file():
        return fail("SOURCE_MISSING", f"source audio missing: {src}", 5)

    expected_sha = str(job.get("reference_sha256") or "").strip()
    if expected_sha and not valid_sha256(expected_sha):
        return fail("REFERENCE_INVALID", f"reference_sha256 must be exactly 64 hexadecimal characters: {expected_sha}", 6)

    actual_sha = sha256_file(src)
    if expected_sha and actual_sha.lower() != expected_sha.lower():
        print(f"expected={expected_sha}", file=sys.stderr)
        print(f"actual={actual_sha}", file=sys.stderr)
        return fail("REFERENCE_INVALID", "reference SHA-256 mismatch", 7)

    media_info = ffprobe_info(src)
    if not media_info.get("available") or media_info.get("error"):
        return fail("REFERENCE_INVALID", f"ffprobe could not validate source audio: {media_info}", 8)

    request_body["src_audio_path"] = str(src)
    request_body["full_analysis_only"] = True
    expected_dit = str(request_body.get("model") or EXPECTED_DIT)
    expected_lm = str(request_body.get("lm_model_path") or EXPECTED_LM)

    try:
        health = http_json(base_url + "/health", timeout=5)
    except Exception as exc:
        return fail("MODEL_NOT_READY", f"API health failed: {exc}", 9)

    health_data = health.get("data") or {}
    ready = (
        health_data.get("models_initialized") is True
        and health_data.get("llm_initialized") is True
        and health_data.get("loaded_model") == expected_dit
        and health_data.get("loaded_lm_model") == expected_lm
    )
    if not ready:
        print("health=" + json.dumps(health_data, ensure_ascii=False), file=sys.stderr)
        return fail("MODEL_NOT_READY", f"expected DiT={expected_dit}, LM={expected_lm}", 10)

    repo_root_text = command_output(["git", "-C", str(job_path.parent), "rev-parse", "--show-toplevel"])
    repo_root = Path(repo_root_text) if repo_root_text else None
    job_commit = command_output(["git", "rev-parse", "HEAD"], cwd=repo_root) if repo_root else None
    runtime = Path(os.path.expanduser(os.getenv("ACESTEP_RUNTIME", DEFAULT_RUNTIME))).resolve()
    acestep_commit = command_output(["git", "rev-parse", "HEAD"], cwd=runtime) if runtime.is_dir() else None
    job_sha = sha256_file(job_path)

    print("REFERENCE_ANALYSIS_START")
    print(f"api={base_url}")
    print(f"source={src}")
    print(f"sha256={actual_sha}")
    print(f"job_sha256={job_sha}")
    print(f"job_commit={job_commit or 'unknown'}")
    print(f"acestep_commit={acestep_commit or 'unknown'}")

    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        submit = http_json(base_url + "/release_task", "POST", request_body, timeout=60)
    except Exception as exc:
        return fail("API_SUBMIT_FAILED", f"release_task failed: {exc}", 11)

    if submit.get("code") != 200 or not isinstance(submit.get("data"), dict):
        print(json.dumps(submit, ensure_ascii=False, indent=2), file=sys.stderr)
        return fail("API_SUBMIT_FAILED", "release_task returned an unexpected payload", 12)

    task_id = submit["data"].get("task_id")
    if not task_id:
        return fail("API_SUBMIT_FAILED", "release_task returned no task_id", 13)

    print(f"task_id={task_id}")
    deadline = time.time() + args.timeout_seconds
    final_item = None
    last_status = object()
    transient_poll_errors = 0

    while time.time() < deadline:
        try:
            query = http_json(base_url + "/query_result", "POST", {"task_id_list": [task_id]}, timeout=30)
            transient_poll_errors = 0
        except Exception as exc:
            transient_poll_errors += 1
            print(f"WARN: query_result temporary failure {transient_poll_errors}: {exc}", file=sys.stderr)
            if transient_poll_errors >= 12:
                return fail("API_POLL_FAILED", "too many consecutive query_result failures", 14)
            time.sleep(args.poll_seconds)
            continue

        data = query.get("data") or []
        item = data[0] if data else {}
        status = item.get("status")
        if status != last_status:
            print(f"status={status}")
            last_status = status
        if status in (1, 2):
            final_item = item
            break
        time.sleep(args.poll_seconds)

    if final_item is None:
        return fail("API_POLL_FAILED", "reference analysis timed out", 15)

    normalized = normalize_result(final_item)
    summary = result_summary(normalized.get("result"))
    normalized.update(
        {
            "analysis_schema_version": 1,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "started_at": started_at,
            "job": {"path": str(job_path), "sha256": job_sha, "git_commit": job_commit},
            "engine": {
                "name": "ace-step",
                "runtime": str(runtime),
                "git_commit": acestep_commit,
                "dit_model": expected_dit,
                "lm_model": expected_lm,
                "backend": request_body.get("lm_backend") or "mlx",
            },
            "reference": {"path": str(src), "sha256": actual_sha, "ffprobe": media_info},
            "health": health_data,
            "request": request_body,
            "summary": summary,
        }
    )

    task_dir = job_path.parent.parent
    out_json = task_dir / "metadata" / "reference-analysis.latest.json"
    out_log = task_dir / "metadata" / "reference-analysis.latest.log"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_lines = [
        "REFERENCE_ANALYSIS_RESULT",
        f"task_id={task_id}",
        f"status={normalized.get('status')}",
        f"reference_sha256={actual_sha}",
        f"job_sha256={job_sha}",
        f"job_commit={job_commit or 'unknown'}",
        f"acestep_commit={acestep_commit or 'unknown'}",
        "summary=" + json.dumps(summary, ensure_ascii=False, indent=2),
    ]
    out_log.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    if normalized.get("status") != 1:
        print(json.dumps(normalized, ensure_ascii=False, indent=2), file=sys.stderr)
        return fail("GENERATION_FAILED", "ACE-Step reference analysis returned failed status", 16)

    result = normalized.get("result")
    if not isinstance(result, dict) or not result.get("audio_codes") or not isinstance(result.get("metas"), dict):
        print(json.dumps(summary, ensure_ascii=False, indent=2), file=sys.stderr)
        return fail("RESULT_INVALID", "analysis succeeded but required audio_codes/metas are missing", 17)

    print("REFERENCE_ANALYSIS_PASS")
    print(f"output={out_json}")
    print("summary=" + json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
