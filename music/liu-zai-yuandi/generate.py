#!/usr/bin/env python3
"""Generate an original song using an existing local ACE-Step 1.5 API.

Python 3.9+ standard library only. API host is restricted to loopback HTTP.
This script never installs models, starts the backend, or uploads audio.
"""
import argparse
import hashlib
import json
import pathlib
import sys
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = pathlib.Path(__file__).resolve().parent


def valid_api_root(url):
    p = urlsplit(url)
    if p.scheme != "http" or p.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("API must be loopback HTTP, e.g. http://127.0.0.1:8001")
    if p.username or p.password or p.query or p.fragment or p.path not in ("", "/"):
        raise ValueError("Use a bare local API origin without paths or credentials")
    return url.rstrip("/")


def req_json(root, endpoint, payload, timeout=30):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(root + endpoint, data=body,
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        obj = json.loads(response.read().decode("utf-8"))
    if obj.get("code") != 200:
        raise RuntimeError("ACE-Step API error for %s: %s" % (endpoint, obj.get("error", obj)))
    return obj


def audio_url(root, file_url):
    p = urlsplit(file_url)
    local = urlsplit(root)
    if p.scheme or p.netloc:
        if p.scheme != local.scheme or p.netloc != local.netloc:
            raise ValueError("Refusing to download from a non-local URL")
    if p.path != "/v1/audio" or not p.query:
        raise ValueError("Unexpected audio download path: %s" % file_url)
    return urlunsplit(("http", local.netloc, p.path, p.query, ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8001")
    parser.add_argument("--out", default=str(ROOT / "output"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--max-polls", type=int, default=120)
    args = parser.parse_args()
    if args.poll_seconds < 0 or args.max_polls < 1:
        parser.error("Invalid polling settings")
    root = valid_api_root(args.api)
    lyrics = (ROOT / "lyrics.txt").read_text(encoding="utf-8").strip()
    conf = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    payload = dict(conf, lyrics=lyrics)
    out = pathlib.Path(args.out).expanduser().resolve()
    if args.dry_run:
        print(json.dumps({"api": root, "output_dir": str(out), "payload": payload},
                         ensure_ascii=False, indent=2))
        return 0

    try:
        with urlopen(Request(root + "/health", method="GET"), timeout=5):
            pass
    except HTTPError as exc:
        if exc.code != 404:
            raise
    except (URLError, TimeoutError) as exc:
        print("Cannot connect to ACE-Step at %s: %s" % (root, exc), file=sys.stderr)
        print("Start your existing ACE-Step server first.", file=sys.stderr)
        return 2

    target = out / "liu_zai_yuandi_v1.mp3"
    if target.exists():
        raise FileExistsError("Audio already exists: %s. Use --out for a new run." % target)
    out.mkdir(parents=True, exist_ok=True)
    (out / "request.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    task = req_json(root, "/release_task", payload, timeout=60)
    (out / "submit.json").write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
    task_id = task.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError("ACE-Step did not return a task_id")
    print("Submitted task %s. Polling local API..." % task_id, flush=True)

    for i in range(args.max_polls):
        time.sleep(args.poll_seconds)
        status = req_json(root, "/query_result", {"task_id_list": [task_id]})
        jobs = status.get("data", [])
        if not jobs:
            print("Poll %d: pending" % (i + 1), flush=True)
            continue
        job = next((j for j in jobs if j.get("task_id") == task_id), jobs[0])
        state = job.get("status")
        print("Poll %d: status=%s" % (i + 1, state), flush=True)
        if state == 2:
            (out / "failed.json").write_text(json.dumps(job, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
            raise RuntimeError("ACE-Step job failed; see output/failed.json")
        if state != 1:
            continue
        result_data = job.get("result", [])
        if isinstance(result_data, str):
            result_data = json.loads(result_data)
        if isinstance(result_data, dict):
            result_data = [result_data]
        if not result_data or not result_data[0].get("file"):
            raise RuntimeError("Task succeeded but returned no audio path")
        uri = audio_url(root, result_data[0]["file"])
        with urlopen(uri, timeout=120) as response:
            audio = response.read()
        if len(audio) < 1000:
            raise RuntimeError("Downloaded audio is suspiciously small")
        if target.exists():
            raise FileExistsError("Refusing to overwrite existing audio: %s" % target)
        target.write_bytes(audio)
        (out / "result.json").write_text(json.dumps(job, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        digest = hashlib.sha256(audio).hexdigest()
        (out / "sha256.txt").write_text("%s  %s\n" % (digest, target.name), encoding="ascii")
        print("SUCCESS: %s\nSHA256: %s" % (target, digest))
        return 0
    print("TIMEOUT: task submitted but still unfinished. Task ID: %s" % task_id, file=sys.stderr)
    print("Inspect output/submit.json and local API logs before retrying.", file=sys.stderr)
    return 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        sys.exit(1)
