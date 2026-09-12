#!/usr/bin/env python3
"""Run one ACE-Step job, create an auditable run directory, and optionally push it.

Only Python stdlib is required. ffmpeg/ffprobe and git are invoked as external tools.
"""

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
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run_id_now() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_cmd(args: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def find_repo_root(start: Path) -> Path:
    result = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=start)
    return Path(result.stdout.strip()).resolve()


def expand_path(value: str, base: Path | None = None) -> str:
    expanded = os.path.expandvars(os.path.expanduser(value))
    p = Path(expanded)
    if not p.is_absolute() and base is not None:
        p = base / p
    return str(p.resolve())


def redact_string(value: str, repo_root: Path) -> str:
    home = str(Path.home())
    repo = str(repo_root)
    value = value.replace(home, "~")
    if repo.startswith(home):
        value = value.replace(repo.replace(home, "~"), "<repo>")
    value = value.replace(repo, "<repo>")
    return value


def redact(value: Any, repo_root: Path) -> Any:
    if isinstance(value, dict):
        return {k: redact(v, repo_root) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, repo_root) for v in value]
    if isinstance(value, str):
        return redact_string(value, repo_root)
    return value


def http_json(method: str, url: str, payload: Any | None = None, timeout: int = 30) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def download(url: str, dest: Path, timeout: int = 1800) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"Accept": "*/*"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out, length=1024 * 1024)


def load_config(config_path: Path) -> dict[str, Any]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def ensure_tooling() -> None:
    missing = [name for name in ("git", "ffmpeg", "ffprobe") if not command_exists(name)]
    if missing:
        raise RuntimeError("缺少命令: " + ", ".join(missing))


def prepare_request(config: dict[str, Any], product_dir: Path) -> dict[str, Any]:
    request = dict(config.get("request") or {})

    prompt_file = request.pop("prompt_file", None)
    lyrics_file = request.pop("lyrics_file", None)

    if prompt_file:
        p = Path(expand_path(str(prompt_file), product_dir))
        request["prompt"] = p.read_text(encoding="utf-8").strip()
    if lyrics_file:
        p = Path(expand_path(str(lyrics_file), product_dir))
        request["lyrics"] = p.read_text(encoding="utf-8").strip()

    for key in ("src_audio_path", "reference_audio_path"):
        if request.get(key):
            request[key] = expand_path(str(request[key]), product_dir)
            if not Path(request[key]).is_file():
                raise FileNotFoundError(f"{key} 文件不存在: {request[key]}")

    if not request.get("prompt"):
        raise ValueError("job 缺少 prompt 或 prompt_file")
    if not request.get("lyrics") and not bool(request.get("instrumental")):
        raise ValueError("job 缺少 lyrics 或 lyrics_file")

    request.setdefault("batch_size", 1)
    request.setdefault("audio_format", "wav")
    request.setdefault("use_random_seed", True)
    request.setdefault("thinking", False)
    return request


def parse_task_id(release_response: dict[str, Any]) -> str:
    data = release_response.get("data") or {}
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError(f"release_task 未返回 task_id: {release_response}")
    return str(task_id)


def get_task_item(query_response: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    data = query_response.get("data")
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict) and str(item.get("task_id")) == task_id:
            return item
    if len(data) == 1 and isinstance(data[0], dict):
        return data[0]
    return None


def parse_result_list(task_item: dict[str, Any]) -> list[dict[str, Any]]:
    raw = task_item.get("result")
    if isinstance(raw, str):
        parsed = json.loads(raw or "[]")
    else:
        parsed = raw
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    return []


def audio_suffix(audio_format: str) -> str:
    fmt = audio_format.lower()
    if fmt == "wav32":
        return ".wav"
    return "." + fmt


def make_preview(source: Path, dest: Path, bitrate: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = run_cmd([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-vn", "-codec:a", "libmp3lame", "-b:a", bitrate,
        str(dest),
    ], check=False)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg 生成 preview 失败:\n" + result.stdout)


def ffprobe_json(source: Path) -> dict[str, Any]:
    result = run_cmd([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)
    ])
    return json.loads(result.stdout)


def publish_git(repo_root: Path, run_dir: Path, run_id: str, auto_push: bool, log) -> str:
    rel = run_dir.relative_to(repo_root)
    run_cmd(["git", "add", "--", str(rel)], cwd=repo_root)

    staged = run_cmd(["git", "diff", "--cached", "--quiet", "--", str(rel)], cwd=repo_root, check=False)
    if staged.returncode == 0:
        log("GIT_NO_CHANGES")
        return ""

    commit = run_cmd(["git", "commit", "-m", f"music: add review run {run_id}"], cwd=repo_root)
    log(commit.stdout.strip())
    sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip()

    if auto_push:
        pushed = run_cmd(["git", "push", "origin", "HEAD"], cwd=repo_root, check=False)
        log(pushed.stdout.strip())
        if pushed.returncode != 0:
            raise RuntimeError("git push 失败，run 已本地 commit: " + sha)
        log(f"GIT_PUSHED commit={sha}")
    return sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="job JSON path")
    args = parser.parse_args()

    ensure_tooling()
    config_path = Path(args.config).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)

    repo_root = find_repo_root(config_path.parent)
    try:
        config_rel = config_path.relative_to(repo_root)
    except ValueError as exc:
        raise RuntimeError("job 配置必须位于当前 Git 仓库内") from exc

    if config_path.parent.name != "config":
        raise RuntimeError("job 配置应放在 products/<type>/<project>/config/ 下")
    product_dir = config_path.parent.parent
    product_rel = product_dir.relative_to(repo_root)

    config = load_config(config_path)
    review = dict(config.get("review") or {})
    api_base = str(config.get("api_base") or "http://127.0.0.1:8001").rstrip("/")
    timeout_seconds = int(config.get("timeout_seconds") or 7200)
    poll_seconds = float(config.get("poll_seconds") or 5)
    preview_bitrate = str(review.get("preview_bitrate") or "192k")
    publish_full_audio = bool(review.get("publish_full_audio", False))
    auto_commit = bool(review.get("auto_commit", True))
    auto_push = bool(review.get("auto_push", True))

    run_id = run_id_now()
    run_dir = product_dir / "runs" / run_id
    work_dir = repo_root / ".work" / product_rel / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    work_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "run.log"

    def log(message: str) -> None:
        line = f"[{utc_now()}] {message}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    started_at = utc_now()
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "running",
        "product": str(product_rel),
        "config": str(config_rel),
        "parent_run_id": config.get("parent_run_id"),
        "started_at": started_at,
        "api_base": api_base,
    }
    write_json(run_dir / "manifest.json", manifest)

    try:
        log(f"RUN_START id={run_id} product={product_rel}")
        log(f"CONFIG {config_rel}")

        health = http_json("GET", api_base + "/health", timeout=5)
        log("API_HEALTH " + json.dumps(health, ensure_ascii=False, separators=(",", ":")))

        request_payload = prepare_request(config, product_dir)
        public_request = redact(request_payload, repo_root)
        write_json(run_dir / "request.json", public_request)
        manifest["request_sha256"] = sha256_json(public_request)
        manifest["model"] = request_payload.get("model")
        manifest["lm_model_path"] = request_payload.get("lm_model_path")
        manifest["task_type"] = request_payload.get("task_type", "text2music")
        manifest["seed"] = request_payload.get("seed", -1)
        manifest["thinking"] = request_payload.get("thinking", False)
        write_json(run_dir / "manifest.json", manifest)

        log("RELEASE_TASK submitting")
        release = http_json("POST", api_base + "/release_task", request_payload, timeout=60)
        write_json(run_dir / "release-response.json", redact(release, repo_root))
        task_id = parse_task_id(release)
        manifest["task_id"] = task_id
        write_json(run_dir / "manifest.json", manifest)
        log(f"TASK_QUEUED task_id={task_id}")

        deadline = time.monotonic() + timeout_seconds
        last_status: int | None = None
        final_query: dict[str, Any] | None = None
        task_item: dict[str, Any] | None = None

        while time.monotonic() < deadline:
            query = http_json("POST", api_base + "/query_result", {"task_id_list": [task_id]}, timeout=30)
            item = get_task_item(query, task_id)
            if item is None:
                log("POLL task missing from response")
                time.sleep(poll_seconds)
                continue

            try:
                status = int(item.get("status", 0))
            except (TypeError, ValueError):
                status = 0

            if status != last_status:
                log(f"TASK_STATUS status={status}")
                last_status = status

            if status in (1, 2):
                final_query = query
                task_item = item
                break
            time.sleep(poll_seconds)
        else:
            raise TimeoutError(f"任务超过 {timeout_seconds}s 仍未结束")

        assert final_query is not None and task_item is not None
        write_json(run_dir / "final-response.json", redact(final_query, repo_root))

        if int(task_item.get("status", 0)) != 1:
            raise RuntimeError("ACE-Step 返回失败状态: " + json.dumps(task_item, ensure_ascii=False))

        result_list = parse_result_list(task_item)
        if not result_list:
            raise RuntimeError("任务成功但 result 中没有音频条目")

        # 当前生产约定 batch_size=1。若未来 batch>1，先保留第一个，同时在 manifest 记录数量。
        result = result_list[0]
        file_url = str(result.get("file") or "")
        if not file_url:
            raise RuntimeError("结果缺少 file URL")
        if file_url.startswith("http://") or file_url.startswith("https://"):
            audio_url = file_url
        else:
            audio_url = urllib.parse.urljoin(api_base + "/", file_url.lstrip("/"))

        fmt = str(request_payload.get("audio_format") or "wav").lower()
        raw_path = work_dir / ("result" + audio_suffix(fmt))
        log(f"DOWNLOAD_AUDIO -> {raw_path.relative_to(repo_root)}")
        download(audio_url, raw_path)
        if raw_path.stat().st_size == 0:
            raise RuntimeError("下载到的音频为空文件")

        raw_sha = sha256_file(raw_path)
        probe = ffprobe_json(raw_path)
        write_json(run_dir / "ffprobe.json", probe)

        preview_path = run_dir / "preview.mp3"
        if raw_path.suffix.lower() == ".mp3":
            shutil.copy2(raw_path, preview_path)
        else:
            make_preview(raw_path, preview_path, preview_bitrate)
        preview_sha = sha256_file(preview_path)

        if publish_full_audio:
            shutil.copy2(raw_path, run_dir / raw_path.name)

        manifest.update({
            "status": "succeeded",
            "finished_at": utc_now(),
            "result_count": len(result_list),
            "raw_audio_format": fmt,
            "raw_audio_sha256": raw_sha,
            "raw_audio_bytes": raw_path.stat().st_size,
            "preview_sha256": preview_sha,
            "preview_bytes": preview_path.stat().st_size,
            "preview_file": "preview.mp3",
            "full_audio_published": publish_full_audio,
            "seed_value": result.get("seed_value"),
            "dit_model": result.get("dit_model") or request_payload.get("model"),
            "lm_model": result.get("lm_model") or request_payload.get("lm_model_path"),
            "metas": result.get("metas"),
        })
        write_json(run_dir / "manifest.json", redact(manifest, repo_root))
        log(f"AUDIO_READY raw_sha256={raw_sha} preview_sha256={preview_sha}")

    except Exception as exc:
        manifest.update({
            "status": "failed",
            "finished_at": utc_now(),
            "error_type": type(exc).__name__,
            "error": redact_string(str(exc), repo_root),
        })
        write_json(run_dir / "manifest.json", manifest)
        log(f"RUN_FAILED {type(exc).__name__}: {exc}")
        if auto_commit:
            try:
                publish_git(repo_root, run_dir, run_id, auto_push, log)
            except Exception as git_exc:
                log(f"GIT_PUBLISH_FAILED {type(git_exc).__name__}: {git_exc}")
        return 1

    if auto_commit:
        try:
            commit_sha = publish_git(repo_root, run_dir, run_id, auto_push, log)
            if commit_sha:
                manifest["git_commit"] = commit_sha
                # manifest 已随 commit 入库，commit SHA 会在下一轮或远端提交记录中可见；避免为写 SHA 再制造一次 commit。
        except Exception as exc:
            log(f"GIT_PUBLISH_FAILED {type(exc).__name__}: {exc}")
            return 2

    log(f"RUN_COMPLETE id={run_id}")
    print()
    print("REVIEW_RUN=" + str(run_dir.relative_to(repo_root)))
    print("LOCAL_FULL_AUDIO=" + str(raw_path))
    print("GIT_PREVIEW=" + str(preview_path.relative_to(repo_root)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nINTERRUPTED", file=sys.stderr)
        raise SystemExit(130)
