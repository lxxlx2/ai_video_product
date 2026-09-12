#!/usr/bin/env python3
"""执行一个 ACE-Step 音乐任务，并生成可提交到 Git 的审核快照。

设计目标：
1. 完整候选保留在 ~/AI/private/music-runs/；
2. Git 只保存轻量 review.mp3、请求、结果、SHA 和日志；
3. 成功和失败都尽量生成 review 快照，便于远端排查；
4. 只依赖 Python 标准库和本机 ffmpeg/ffprobe。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid


def now_text() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def http_json(url: str, method: str = "GET", payload: dict | None = None, timeout: int = 30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve_text(job_path: Path, value: str | None, file_value: str | None) -> str:
    if file_value:
        p = Path(os.path.expanduser(file_value))
        if not p.is_absolute():
            p = (job_path.parent / p).resolve()
        return p.read_text(encoding="utf-8")
    return value or ""


def read_server_delta(path: Path, start_offset: int) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as f:
        size = path.stat().st_size
        if start_offset > size:
            start_offset = 0
        f.seek(start_offset)
        return f.read().decode("utf-8", errors="replace")


def ffprobe_info(path: Path) -> dict:
    if not shutil.which("ffprobe"):
        return {"warning": "ffprobe not found"}
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels",
        "-of", "json", str(path),
    ]
    try:
        return json.loads(subprocess.check_output(cmd, text=True))
    except Exception as e:
        return {"ffprobe_error": str(e)}


def transcode_review(src: Path, dst: Path, bitrate: str = "256k") -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(src),
            "-c:a", "libmp3lame", "-b:a", bitrate,
            str(dst),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job", help="job JSON 路径")
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))

    if not job.get("ready_to_run", False):
        print("ERROR: job ready_to_run=false. Refusing to generate.", file=sys.stderr)
        return 2

    task_dir_value = job.get("task_dir", "..")
    task_dir = Path(os.path.expanduser(task_dir_value))
    if not task_dir.is_absolute():
        task_dir = (job_path.parent / task_dir).resolve()

    base_url = job.get("api", {}).get("base_url", "http://127.0.0.1:8001").rstrip("/")
    server_log = Path(os.path.expanduser(job.get("api", {}).get("server_log", "~/AI/logs/music/acestep-api.log")))
    request_body = dict(job.get("request", {}))
    request_body["prompt"] = resolve_text(job_path, request_body.get("prompt"), job.get("prompt_file"))
    request_body["lyrics"] = resolve_text(job_path, request_body.get("lyrics"), job.get("lyrics_file"))

    if not request_body.get("prompt"):
        print("ERROR: empty prompt", file=sys.stderr)
        return 3
    if not request_body.get("lyrics") and request_body.get("task_type", "text2music") != "extract":
        print("ERROR: empty lyrics", file=sys.stderr)
        return 4

    expected_reference_sha = job.get("reference_sha256")
    src_audio = request_body.get("src_audio_path")
    reference_audio = request_body.get("reference_audio_path")
    checked_reference = src_audio or reference_audio
    if checked_reference:
        ref = Path(os.path.expanduser(checked_reference)).resolve()
        if not ref.exists():
            print(f"ERROR: reference/source audio missing: {ref}", file=sys.stderr)
            return 5
        request_body["src_audio_path" if src_audio else "reference_audio_path"] = str(ref)
        actual = sha256_file(ref)
        if expected_reference_sha and actual.lower() != expected_reference_sha.lower():
            print("ERROR: reference SHA-256 mismatch", file=sys.stderr)
            print(f"expected: {expected_reference_sha}", file=sys.stderr)
            print(f"actual:   {actual}", file=sys.stderr)
            return 6

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    private_root = Path(os.path.expanduser(job.get("private_run_root", "~/AI/private/music-runs")))
    task_slug = job.get("task_slug", task_dir.name)
    run_dir = private_root / task_slug / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    review_rel = Path(job.get("review", {}).get("directory", "review/latest"))
    review_dir = task_dir / review_rel
    review_dir.mkdir(parents=True, exist_ok=True)

    runner_log = run_dir / "runner.log"
    started_at = now_text()
    server_offset = server_log.stat().st_size if server_log.exists() else 0
    task_id = None
    last_query = None
    parsed_result = None
    candidate_path: Path | None = None
    candidate_sha = None
    error_text = None

    def log(msg: str):
        line = f"[{now_text()}] {msg}"
        print(line, flush=True)
        with runner_log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def write_json(path: Path, obj) -> None:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def finalize_review(status: str) -> None:
        nonlocal parsed_result

        server_delta = read_server_delta(server_log, server_offset)
        (run_dir / "server.log").write_text(server_delta, encoding="utf-8")

        if not (run_dir / "result.json").exists():
            write_json(run_dir / "result.json", parsed_result if parsed_result is not None else {})

        probe = ffprobe_info(candidate_path) if candidate_path and candidate_path.exists() else {}
        run_meta = {
            "run_id": run_id,
            "status": status,
            "error": error_text,
            "started_at": started_at,
            "ended_at": now_text(),
            "task_id": task_id,
            "job_file": str(job_path),
            "candidate_local_path": str(candidate_path) if candidate_path else None,
            "candidate_sha256": candidate_sha,
            "candidate_size": candidate_path.stat().st_size if candidate_path and candidate_path.exists() else None,
            "ffprobe": probe,
            "request": request_body,
            "api_query_response": last_query,
        }
        write_json(run_dir / "run.json", run_meta)

        known_review_files = [
            "review.mp3", "request.json", "result.json", "run.json", "runner.log", "server.log"
        ]
        for name in known_review_files:
            p = review_dir / name
            if p.exists() or p.is_symlink():
                p.unlink()

        for name in ["request.json", "result.json", "run.json", "runner.log", "server.log"]:
            src = run_dir / name
            if src.exists():
                shutil.copy2(src, review_dir / name)

        if candidate_path and candidate_path.exists():
            try:
                transcode_review(
                    candidate_path,
                    review_dir / "review.mp3",
                    job.get("review", {}).get("mp3_bitrate", "256k"),
                )
            except Exception as e:
                log(f"WARN review mp3 transcode failed: {e}")

        # runner.log 在 finalize 过程中可能新增行，再复制一次。
        shutil.copy2(runner_log, review_dir / "runner.log")

    log(f"run_id={run_id}")
    log(f"job={job_path}")
    log(f"api={base_url}")
    log(f"task_type={request_body.get('task_type', 'text2music')}")
    log(f"model={request_body.get('model')}")
    log(f"lm_model_path={request_body.get('lm_model_path')}")
    write_json(run_dir / "request.json", request_body)

    try:
        health = http_json(base_url + "/health", timeout=5)
        log(f"health={json.dumps(health, ensure_ascii=False)}")
    except Exception as e:
        error_text = f"health check failed: {e}"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 10

    try:
        submit = http_json(base_url + "/release_task", "POST", request_body, timeout=60)
        write_json(run_dir / "submit_response.json", submit)
    except Exception as e:
        error_text = f"release_task failed: {e}"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 11

    if submit.get("code") != 200 or not isinstance(submit.get("data"), dict):
        error_text = f"unexpected submit response: {submit}"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 12

    task_id = submit["data"].get("task_id")
    if not task_id:
        error_text = "task_id missing"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 13

    log(f"task_id={task_id}")
    deadline = time.time() + args.timeout_seconds
    last_status = object()

    while time.time() < deadline:
        try:
            last_query = http_json(
                base_url + "/query_result",
                "POST",
                {"task_id_list": [task_id]},
                timeout=30,
            )
        except Exception as e:
            log(f"WARN query_result failed: {e}")
            time.sleep(args.poll_seconds)
            continue

        data = last_query.get("data") or []
        item = data[0] if data else {}
        status = item.get("status")
        if status != last_status:
            log(f"status={status}")
            last_status = status
        if status in (1, 2):
            break
        time.sleep(args.poll_seconds)
    else:
        error_text = "timeout waiting for generation"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 14

    write_json(run_dir / "query_response.json", last_query)
    item = (last_query.get("data") or [{}])[0]

    raw_result = item.get("result", "[]")
    try:
        parsed_result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
    except Exception:
        parsed_result = {"raw_result": raw_result}
    write_json(run_dir / "result.json", parsed_result)

    if item.get("status") != 1:
        error_text = f"generation failed: {item}"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 15

    result_item = None
    if isinstance(parsed_result, list):
        for candidate in parsed_result:
            if isinstance(candidate, dict) and candidate.get("file"):
                result_item = candidate
                break
    elif isinstance(parsed_result, dict) and parsed_result.get("file"):
        result_item = parsed_result

    if not result_item:
        error_text = "no downloadable audio URL found in result"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 16

    file_url = result_item["file"]
    if file_url.startswith("/"):
        file_url = base_url + file_url

    audio_format = str(request_body.get("audio_format", "wav")).lower()
    suffix = ".wav" if audio_format == "wav32" else "." + audio_format
    candidate_path = run_dir / ("candidate" + suffix)

    try:
        log(f"downloading={file_url}")
        urllib.request.urlretrieve(file_url, candidate_path)
    except Exception as e:
        error_text = f"audio download failed: {e}"
        log(f"ERROR {error_text}")
        finalize_review("failed")
        return 17

    candidate_sha = sha256_file(candidate_path)
    log(f"candidate={candidate_path}")
    log(f"candidate_sha256={candidate_sha}")
    log("MUSIC_JOB_PASS")
    finalize_review("succeeded")

    print()
    print("MUSIC_JOB_PASS")
    print(f"RUN_ID={run_id}")
    print(f"CANDIDATE={candidate_path}")
    print(f"CANDIDATE_SHA256={candidate_sha}")
    print(f"REVIEW_DIR={review_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
