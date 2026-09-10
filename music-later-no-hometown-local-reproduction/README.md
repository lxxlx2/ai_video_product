# 后来没有故乡 · Local Reproduction

This task records a reproducible local workflow for rebuilding the approved reference song with ACE-Step 1.5 on Apple Silicon, and serves as the first concrete local music-generation workflow for future original songs.

## Goal

Start from the Owner-selected Suno reference file and produce a close local reproduction with controllable lyrics, structure, vocal character, arrangement, seeds, and local repaint/edit passes.

The same ACE-Step runtime will later support original text/lyrics-to-song creation without requiring a Suno reference.

The target for this task is musical similarity and iterative control. Exact waveform-level duplication is not assumed.

Long-term operation is Codex-led: the Owner discusses the song, reviews results and approves one exact candidate. Codex handles local model calls, candidate iteration, Git publication and cleanup. See [`docs/CODEX_ORCHESTRATION.md`](docs/CODEX_ORCHESTRATION.md).

## Runtime boundary

- ACE-Step lives in its own runtime directory and environment.
- The service binds to localhost only.
- The reference M4A, derived WAV, stems, model weights, caches, and unapproved output audio stay local during work.
- Scripts never kill unrelated processes or modify unrelated runtimes.
- No paid/cloud fallback is enabled.
- Current execution does not require proving simultaneous coexistence with the older Qwen stack. Future platform-wide routing can be revisited after the `codex-web-bridge` direction is settled.

Architecture record: `lxxlx2/local-ai-platform/docs/architecture/ADR-0007-local-music-generation-and-reference-reproduction.md` on branch `feat/local-music-reproduction-v01`.

## Reference

Expected local source filename:

```text
后来没有故乡.m4a
```

Verified technical metadata for the selected reference:

```text
duration: 335.840 s
container: M4A/MP4
codec: Opus
sample rate: 48000 Hz
channels: stereo
audio bitrate: about 127.5 kbps
sha256: 176c81b30cbd68de6cd7c900d1513160f9a6a591eb7e9bed65d848f273c48b0e
```

The reference audio itself is intentionally not committed to the public repository.

## First deployment

From the confirmed local repository path:

```bash
cd /Users/jerson/ai_video_product
git fetch origin
git switch feat/local-music-reproduction-v01
git pull --ff-only

cd music-later-no-hometown-local-reproduction
bash scripts/preflight_macos.sh
bash scripts/bootstrap_acestep_macos.sh
bash scripts/prepare_reference.sh "/path/to/后来没有故乡.m4a"
bash scripts/launch_acestep_macos.sh smoke
```

The smoke profile proves the isolated runtime first. When it works, stop it with `Ctrl+C` and continue:

```bash
bash scripts/launch_acestep_macos.sh repro
```

Open the local Gradio UI shown by the launcher, normally:

```text
http://127.0.0.1:8215
```

## Reproduction sequence

Use [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md):

1. verify source hash and convert a local 48 kHz WAV working copy;
2. start with the `repro` profile;
3. run Audio Understanding and record BPM/key/time-signature/caption;
4. run reference-guided generation using `generated/lyrics.txt` and `generated/style.txt`;
5. run Remix against the full local reference;
6. generate multiple seeds and keep the closest candidate;
7. use Repaint only for weak regions;
8. try the `quality` profile when useful;
9. keep parameters and hashes only while the task is active;
10. select one final product and publish only that approved audio as the durable per-song product.

## Profiles

| Profile | DiT | LM | Purpose |
|---|---|---|---|
| `smoke` | `acestep-v15-turbo` | `acestep-5Hz-lm-0.6B` | installation/runtime proof |
| `repro` | `acestep-v15-xl-turbo` | `acestep-5Hz-lm-1.7B` | first real reference/remix attempts |
| `quality` | `acestep-v15-xl-sft` | `acestep-5Hz-lm-4B` | higher-quality candidate |

## Git audio policy

Git can store the final audio. This repository tracks approved audio through Git LFS for WAV, FLAC, M4A, MP3, AAC, and OGG.

Preferred final master:

```text
output/final.wav
```

The completed-song target is one local `final.wav` plus one Git LFS `final.wav` containing identical approved bytes. Rejected candidates, task-specific prompts/config, stems, repaint fragments, converted references, logs and caches are removed after remote verification. See [`docs/RETENTION_AND_CLEANUP.md`](docs/RETENTION_AND_CLEANUP.md).

## Files

- `generated/lyrics.txt`: current lyrics used during the active reproduction task.
- `generated/style.txt`: current style/vocal prompt used during active work.
- `config/reproduction.json`: active-task reproduction configuration.
- `metadata/reference.json`: safe technical source record and SHA-256 during the active task.
- `metadata/preflight-2026-09-10.md`: first successful Apple Silicon preflight evidence.
- `scripts/preflight_macos.sh`: read-only host/runtime preflight.
- `scripts/bootstrap_acestep_macos.sh`: isolated pinned ACE-Step install.
- `scripts/prepare_reference.sh`: source verification and local WAV preparation.
- `scripts/launch_acestep_macos.sh`: foreground smoke/repro/quality launcher.
- `docs/REPRODUCTION_RUNBOOK.md`: detailed step-by-step reproduction process.
- `docs/CODEX_ORCHESTRATION.md`: target hands-off Codex orchestration architecture.
- `docs/RETENTION_AND_CLEANUP.md`: final-only product retention and cleanup policy.

Task-specific lyrics, style, configs and source metadata are working artifacts. They can be deleted from the completed task after final publication when the strict one-product-file end state is used. Shared generic workflow documentation and scripts remain repository infrastructure.

## Current status

The first read-only Apple Silicon preflight passed on 2026-09-10. Verified at that point: arm64, macOS 26.6.2, git/ffmpeg/ffprobe/shasum/lsof/uv present, about 48 GiB physical memory, 72% system-wide memory free, about 511 GiB free disk space, and port 8215 available. See `metadata/preflight-2026-09-10.md`.

ACE-Step bootstrap is currently being executed on the Owner machine. Local model generation and quality validation are still pending. No existing unrelated runtime has been modified by the repository changes or preflight.