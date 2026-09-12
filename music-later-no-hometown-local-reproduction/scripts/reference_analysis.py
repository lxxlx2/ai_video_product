#!/usr/bin/env python3
"""Run ACE-Step full reference analysis and write a Git-friendly metadata snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value or ""))


def http_json(url: str, method: str = "GET", payload: dict | None = None, timeout: int = 30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


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

    return {
        "task_id": item.get("task_id"),
        "status": item.get("status"),
        "result": parsed,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--poll-seconds", type=int, default=5)
    ap.add_argument("--timeout-seconds", type=int, default=3600)
    args = ap.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    base_url = job.get("api", {}).get("base_url", "http://127.0.0.1:8001").rstrip("/")
    request_body = dict(job.get("request", {}))

    src = Path(os.path.expanduser(request_body.get("src_audio_path", ""))).resolve()
    if not src.exists():
        print(f"ERROR: source audio missing: {src}", file=sys.stderr)
        return 2

    expected_sha = job.get("reference_sha256")
    if expected_sha and not valid_sha256(expected_sha):
        print("ERROR: configured reference_sha256 is malformed; expected exactly 64 hexadecimal characters", file=sys.stderr)
        print(f"configured: {expected_sha}", file=sys.stderr)
        print(f"length:     {len(expected_sha)}", file=sys.stderr)
        return 3

    actual_sha = sha256_file(src)
    if expected_sha and actual_sha.lower() != expected_sha.lower():
        print("ERROR: reference SHA-256 mismatch", file=sys.stderr)
        print(f"expected: {expected_sha}", file=sys.stderr)
        print(f"actual:   {actual_sha}", file=sys.stderr)
        return 4

    request_body["src_audio_path"] = str(src)
    request_body["full_analysis_only"] = True

    try:
        health = http_json(base_url + "/health", timeout=5)
    except Exception as e:
        print(f"ERROR: API health failed: {e}", file=sys.stderr)
        return 5

    print("REFERENCE_ANALYSIS_START")
    print(f"api={base_url}")
    print(f"source={src}")
    print(f"sha256={actual_sha}")
    print(f"health={json.dumps(health, ensure_ascii=False)}")

    submit = http_json(base_url + "/release_task", "POST", request_body, timeout=60)
    if submit.get("code") != 200 or not isinstance(submit.get("data"), dict):
        print(json.dumps(submit, ensure_ascii=False, indent=2))
        return 6

    task_id = submit["data"].get("task_id")
    if not task_id:
        print("ERROR: no task_id", file=sys.stderr)
        return 7

    print(f"task_id={task_id}")
    deadline = time.time() + args.timeout_seconds
    final_item = None
    last_status = object()

    while time.time() < deadline:
        q = http_json(
            base_url + "/query_result",
            "POST",
            {"task_id_list": [task_id]},
            timeout=30,
        )
        data = q.get("data") or []
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
        print("ERROR: analysis timeout", file=sys.stderr)
        return 8

    normalized = normalize_result(final_item)
    normalized["reference"] = {
        "path": str(src),
        "sha256": actual_sha,
    }
    normalized["request"] = request_body
    normalized["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    task_dir = job_path.parent.parent
    out_json = task_dir / "metadata" / "reference-analysis.latest.json"
    out_log = task_dir / "metadata" / "reference-analysis.latest.log"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "REFERENCE_ANALYSIS_RESULT",
        f"task_id={task_id}",
        f"status={normalized.get('status')}",
        f"reference_sha256={actual_sha}",
        json.dumps(normalized.get("result"), ensure_ascii=False, indent=2),
    ]
    out_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if normalized.get("status") != 1:
        print(json.dumps(normalized, ensure_ascii=False, indent=2))
        return 9

    print("REFERENCE_ANALYSIS_PASS")
    print(f"output={out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
