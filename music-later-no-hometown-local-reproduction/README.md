# 后来没有故乡 · Local Reproduction

This task records a reproducible local workflow for rebuilding the approved reference song with ACE-Step 1.5 on Apple Silicon, and serves as the first concrete local music-generation workflow for future original songs.

## Goal

Start from the Owner-selected Suno reference file and produce a close local reproduction with controllable lyrics, structure, vocal character, arrangement, seeds, and local repaint/edit passes.

The same ACE-Step runtime will later support original text/lyrics-to-song creation without requiring a Suno reference.

The target for this task is musical similarity and iterative control. Exact waveform-level duplication is not assumed.

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
```

The first host preflight and isolated ACE-Step bootstrap have passed. Because the Owner does not currently require coexistence with the older heavy-model stack, downloading a disposable small smoke model is optional. The next useful runtime gate is a real generation using the intended high-quality profile.

Recommended next launch:

```bash
bash scripts/launch_acestep_macos.sh quality
```

Open the local Gradio UI shown by the launcher, normally:

```text
http://127.0.0.1:8215
```

## Reproduction sequence

Use [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md):

1. verify source hash and convert a local 48 kHz WAV working copy;
2. start the intended generation profile;
3. run Audio Understanding and record BPM/key/time-signature/caption;
4. run reference-guided generation using `generated/lyrics.txt` and `generated/style.txt`;
5. run Remix against the full local reference;
6. generate multiple seeds and keep the closest candidate;
7. use Repaint only for weak regions;
8. preserve parameters and hashes for candidates worth keeping;
9. select one final product and publish only that approved audio plus lightweight metadata;
10. after remote Git/LFS verification, delete task intermediates.

## Profiles

| Profile | DiT | LM | Purpose |
|---|---|---|---|
| `smoke` | `acestep-v15-turbo` | `acestep-5Hz-lm-0.6B` | optional lightweight runtime proof |
| `repro` | `acestep-v15-xl-turbo` | `acestep-5Hz-lm-1.7B` | faster real reference/remix attempts |
| `quality` | `acestep-v15-xl-sft` | `acestep-5Hz-lm-4B` | preferred high-quality local creation/reproduction profile |

## Git audio policy

Git can store the final audio. This repository tracks approved audio through Git LFS for WAV, FLAC, M4A, MP3, AAC, and OGG.

Preferred final master:

```text
output/final.wav
```

Optional delivery copies may also be retained as `final.flac`, `final.m4a`, or `final.mp3` when useful.

Rejected candidates, stems, repaint fragments, temporary WAV conversions, logs, caches, and other working files stay local and are deleted after the final Git-backed artifact has been pushed and verified. See [`docs/RETENTION_AND_CLEANUP.md`](docs/RETENTION_AND_CLEANUP.md).

## Files

- `generated/lyrics.txt`: current lyrics used for local reproduction.
- `generated/style.txt`: concise style/vocal prompt.
- `config/reproduction.json`: pinned upstream revision, profiles, paths, source metadata, and reproduction targets.
- `metadata/reference.json`: safe technical source record and SHA-256.
- `metadata/preflight-2026-09-10.md`: first successful Apple Silicon preflight evidence.
- `metadata/bootstrap-2026-09-11.md`: successful isolated ACE-Step dependency/bootstrap evidence.
- `scripts/preflight_macos.sh`: read-only host/runtime preflight.
- `scripts/bootstrap_acestep_macos.sh`: isolated pinned ACE-Step install.
- `scripts/prepare_reference.sh`: source verification and local WAV preparation.
- `scripts/launch_acestep_macos.sh`: foreground smoke/repro/quality launcher.
- `docs/REPRODUCTION_RUNBOOK.md`: detailed step-by-step reproduction process.
- `docs/RETENTION_AND_CLEANUP.md`: final-artifact retention and cleanup policy.
- `docs/CODEX_ORCHESTRATION.md`: target autonomous Codex workflow after `codex-web-bridge` is ready.

## Current status

Host preflight: `PASS`.

ACE-Step bootstrap: `PASS`.

Installed isolated runtime:

```text
/Users/jerson/AI/runtime/music/acestep-1.5
```

Pinned ACE-Step commit:

```text
ca1e85fe9430179831e6bc6be790c332190a3866
```

Installed environment includes CPython 3.12.14, ACE-Step 1.5.0, MLX 0.30.6 and mlx-lm 0.29.1. Model-weight download and first successful music generation remain pending.

Next step: prepare the exact approved reference audio, then launch the preferred `quality` profile and complete one real local generation.
