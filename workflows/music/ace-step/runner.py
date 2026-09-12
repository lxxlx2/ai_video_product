#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from typing import Any


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def cmd(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def expand_path(value: str, base: Path) -> str:
    p = Path(os.path.expandvars(os.path.expanduser(value)))
    if not p.is_absolute():
        p = base / p
    return str(p.resolve())


def redact(value: Any, repo_root: Path) -> Any:
    if isinstance(value, dict):
        return {k: redact(v, repo_root) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, repo_root) for v in value]
    if isinstance(value, str):
        home = str(Path.home())
        repo = str(repo_root)
        return value.replace(repo, "<repo>").replace(home, "~")
    return value


def http_json(method: str, url: str, payload: Any | None = None, timeout: int = 60) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=1800) as resp, path.open("wb") as f:
        shutil.copyfileobj(resp, f, length=1024 * 1024)


def load_request(config: dict[str, Any], product_dir: Path) -> dict[str, Any]:
    req = dict(config.get("request") or {})
    prompt_file = req.pop("prompt_file", None)
    lyrics_file = req.pop("lyrics_file", None)

    if prompt_file:
        req["prompt"] = Path(expand_path(str(prompt_file), product_dir)).read_text(encoding="utf-8").strip()
    if lyrics_file:
        req["lyrics"] = Path(expand_path(str(lyrics_file), product_dir)).read_text(encoding="utf-8").strip()

    for key in ("src_audio_path", "reference_audio_path"):
        if req.get(key):
            req[key] = expand_path(str(req[key]), product_dir)
            if not Path(req[key]).is_file():
                raise FileNotFoundError(f"{key} 不存在: {req[key]}")

    if not req.get("prompt"):
        raise ValueError("缺少 prompt 或 prompt_file")
    if not req.get("lyrics") and not req.get("instrumental"):
        raise ValueError("缺少 lyrics 或 lyrics_file")

    req.setdefault("batch_size", 1)
    req.setdefault("audio_format", "wav")
    req.setdefault("use_random_seed", True)
    req.setdefault("thinking", False)
    return req


def task_item(query: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    data = query.get("data")
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict) and str(item.get("task_id")) == task_id:
            return item
    if len(data) == 1 and isinstance(data[0], dict):
        return data[0]
    return None


def result_items(item: dict[str, Any]) -> list[dict[str, Any]]:
    value = item.get("result")
    if isinstance(value, str):
        value = json.loads(value or "[]")
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    return []


def ffprobe(path: Path) -> dict[str, Any]:
    p = cmd(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    return json.loads(p.stdout)


def preview_mp3(source: Path, target: Path, bitrate: str) -> None:
    p = cmd([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-vn", "-codec:a", "libmp3lame", "-b:a", bitrate, str(target),
    ], check=False)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg preview 失败: " + p.stdout)


def publish(repo_root: Path, run_dir: Path, rid: str, push: bool) -> str:
    rel = run_dir.relative_to(repo_root)
    cmd(["git", "add", "--", str(rel)], cwd=repo_root)
    diff = cmd(["git", "diff", "--cached", "--quiet", "--", str(rel)], cwd=repo_root, check=False)
    if diff.returncode == 0:
        return ""
    cmd(["git", "commit", "-m", f"music: add review run {rid}"], cwd=repo_root)
    sha = cmd(["git", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    if push:
        p = cmd(["git", "push", "origin", "HEAD"], cwd=repo_root, check=False)
        if p.returncode != 0:
            raise RuntimeError(f"git push 失败，已本地 commit {sha}: {p.stdout}")
    return sha


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    args = ap.parse_args()

    for name in ("git", "ffmpeg", "ffprobe"):
        if shutil.which(name) is None:
            raise RuntimeError(f"缺少命令: {name}")

    config_path = Path(args.config).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    repo_root = Path(cmd(["git", "rev-parse", "--show-toplevel"], cwd=config_path.parent).stdout.strip()).resolve()
    config_path.relative_to(repo_root)

    if config_path.parent.name != "config":
        raise RuntimeError("job 必须位于 products/<type>/<project>/config/ 下")

    product_dir = config_path.parent.parent
    product_rel = product_dir.relative_to(repo_root)
    review = dict(config.get("review") or {})
    base = str(config.get("api_base") or "http://127.0.0.1:8001").rstrip("/")
    poll_seconds = float(config.get("poll_seconds") or 5)
    timeout_seconds = int(config.get("timeout_seconds") or 7200)
    publish_full = bool(review.get("publish_full_audio", False))
    auto_commit = bool(review.get("auto_commit", True))
    auto_push = bool(review.get("auto_push", True))
    bitrate = str(review.get("preview_bitrate") or "192k")

    rid = run_id()
    review_dir = product_dir / "runs" / rid
    work_dir = repo_root / ".work" / product_rel / rid
    review_dir.mkdir(parents=True)
    work_dir.mkdir(parents=True)
    log_path = review_dir / "run.log"

    def log(text: str) -> None:
        line = f"[{now()}] {text}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": rid,
        "status": "running",
        "product": str(product_rel),
        "config": str(config_path.relative_to(repo_root)),
        "parent_run_id": config.get("parent_run_id"),
        "started_at": now(),
    }
    write_json(review_dir / "manifest.json", manifest)
    raw_path: Path | None = None

    try:
        log(f"RUN_START {rid}")
        health = http_json("GET", base + "/health", timeout=5)
        log("API_HEALTH " + json.dumps(health, ensure_ascii=False, separators=(",", ":")))

        req = load_request(config, product_dir)
        write_json(review_dir / "request.json", redact(req, repo_root))
        manifest.update({
            "model": req.get("model"),
            "lm_model_path": req.get("lm_model_path"),
            "task_type": req.get("task_type", "text2music"),
            "thinking": req.get("thinking", False),
            "seed": req.get("seed", -1),
        })
        write_json(review_dir / "manifest.json", manifest)

        log("RELEASE_TASK")
        release = http_json("POST", base + "/release_task", req, timeout=60)
        write_json(review_dir / "release-response.json", redact(release, repo_root))
        tid = str((release.get("data") or {}).get("task_id") or "")
        if not tid:
            raise RuntimeError("release_task 未返回 task_id")
        manifest["task_id"] = tid
        write_json(review_dir / "manifest.json", manifest)
        log(f"TASK_ID {tid}")

        deadline = time.monotonic() + timeout_seconds
        last_status: int | None = None
        final_query: dict[str, Any] | None = None
        final_item: dict[str, Any] | None = None

        while time.monotonic() < deadline:
            query = http_json("POST", base + "/query_result", {"task_id_list": [tid]}, timeout=30)
            item = task_item(query, tid)
            if item is None:
                time.sleep(poll_seconds)
                continue
            status = int(item.get("status", 0) or 0)
            if status != last_status:
                log(f"TASK_STATUS {status}")
                last_status = status
            if status in (1, 2):
                final_query, final_item = query, item
                break
            time.sleep(poll_seconds)

        if final_query is None or final_item is None:
            raise TimeoutError(f"任务超过 {timeout_seconds}s")

        write_json(review_dir / "final-response.json", redact(final_query, repo_root))
        if int(final_item.get("status", 0) or 0) != 1:
            raise RuntimeError("ACE-Step 任务失败")

        items = result_items(final_item)
        if not items:
            raise RuntimeError("成功响应中没有音频结果")
        first = items[0]
        file_url = str(first.get("file") or "")
        if not file_url:
            raise RuntimeError("结果缺少 file URL")
        audio_url = file_url if file_url.startswith("http") else urllib.parse.urljoin(base + "/", file_url.lstrip("/"))

        fmt = str(req.get("audio_format") or "wav").lower()
        suffix = ".wav" if fmt == "wav32" else "." + fmt
        raw_path = work_dir / ("result" + suffix)
        log("DOWNLOAD_AUDIO")
        download(audio_url, raw_path)
        if raw_path.stat().st_size == 0:
            raise RuntimeError("音频为空")

        write_json(review_dir / "ffprobe.json", ffprobe(raw_path))
        preview = review_dir / "preview.mp3"
        if raw_path.suffix.lower() == ".mp3":
            shutil.copy2(raw_path, preview)
        else:
            preview_mp3(raw_path, preview, bitrate)

        if publish_full:
            shutil.copy2(raw_path, review_dir / raw_path.name)

        manifest.update({
            "status": "succeeded",
            "finished_at": now(),
            "raw_audio_sha256": sha256_file(raw_path),
            "raw_audio_bytes": raw_path.stat().st_size,
            "preview_sha256": sha256_file(preview),
            "preview_bytes": preview.stat().st_size,
            "preview_file": "preview.mp3",
            "full_audio_published": publish_full,
            "seed_value": first.get("seed_value"),
            "dit_model": first.get("dit_model") or req.get("model"),
            "lm_model": first.get("lm_model") or req.get("lm_model_path"),
            "metas": first.get("metas"),
        })
        write_json(review_dir / "manifest.json", redact(manifest, repo_root))
        log("RUN_SUCCEEDED")

    except Exception as exc:
        manifest.update({
            "status": "failed",
            "finished_at": now(),
            "error_type": type(exc).__name__,
            "error": str(exc).replace(str(Path.home()), "~"),
        })
        write_json(review_dir / "manifest.json", manifest)
        log(f"RUN_FAILED {type(exc).__name__}: {exc}")
        if auto_commit:
            try:
                publish(repo_root, review_dir, rid, auto_push)
            except Exception as git_exc:
                print(f"GIT_PUBLISH_FAILED: {git_exc}", file=sys.stderr)
        return 1

    if auto_commit:
        sha = publish(repo_root, review_dir, rid, auto_push)
        if sha:
            print(f"GIT_COMMIT={sha}")

    print(f"REVIEW_RUN={review_dir.relative_to(repo_root)}")
    if raw_path is not None:
        print(f"LOCAL_FULL_AUDIO={raw_path}")
    print(f"GIT_PREVIEW={review_dir.relative_to(repo_root)}/preview.mp3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
