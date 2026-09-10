# 后来没有故乡 · Local Reproduction

This task records a reproducible local workflow for rebuilding the approved reference song with ACE-Step 1.5 on Apple Silicon while preserving the existing local AI platform.

## Goal

Start from the Owner-selected Suno reference file and produce a close local reproduction with controllable lyrics, structure, vocal character, arrangement, seeds, and local repaint/edit passes.

The target is musical similarity and iterative control. Exact waveform-level duplication is not assumed.

## Safety boundary

- Existing local-ai-platform services are not modified or restarted by this task.
- ACE-Step lives in its own runtime directory and environment.
- The service binds to localhost only.
- The reference M4A, derived WAV, stems, model weights, caches, and unapproved output audio stay local.
- Scripts never kill unrelated processes or close user applications.
- Heavy music generation is on-demand. Normal desktop work keeps priority.
- No paid/cloud fallback is enabled.

Architecture decision: `lxxlx2/local-ai-platform/docs/architecture/ADR-0007-local-music-generation-and-reference-reproduction.md` on branch `feat/local-music-reproduction-v01`.

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

The audio itself is intentionally not committed to this public repository.

## First deployment

From a local clone of this repository:

```bash
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

Use the workflow in [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md):

1. verify source hash and convert a local 48 kHz WAV working copy;
2. start with the `repro` profile;
3. run Audio Understanding and record BPM/key/time-signature/caption;
4. run a reference-guided generation using `generated/lyrics.txt` and `generated/style.txt`;
5. run Cover against the full local reference;
6. generate multiple seeds and keep the closest candidate;
7. use Repaint only for weak regions;
8. if the workstation remains healthy, try the `quality` profile;
9. preserve parameters and hashes for every candidate worth keeping;
10. publish an audio master only after explicit Owner approval.

## Profiles

| Profile | DiT | LM | Purpose |
|---|---|---|---|
| `smoke` | `acestep-v15-turbo` | `acestep-5Hz-lm-0.6B` | installation/runtime proof |
| `repro` | `acestep-v15-xl-turbo` | `acestep-5Hz-lm-1.7B` | first real reference/cover attempts |
| `quality` | `acestep-v15-xl-sft` | `acestep-5Hz-lm-4B` | higher-quality candidate after resource evidence |

The `quality` profile is not automatically production-safe merely because the machine has 48 GiB unified memory. Keep normal applications open and treat resource pressure as valid evidence.

## Files

- `generated/lyrics.txt`: current single-version lyrics used for local reproduction.
- `generated/style.txt`: concise style/vocal prompt.
- `config/reproduction.json`: pinned upstream revision, profiles, paths, source metadata, and reproduction targets.
- `metadata/reference.json`: safe technical source record and SHA-256.
- `scripts/preflight_macos.sh`: read-only host/runtime preflight.
- `scripts/bootstrap_acestep_macos.sh`: isolated pinned ACE-Step install.
- `scripts/prepare_reference.sh`: source verification and local WAV preparation.
- `scripts/launch_acestep_macos.sh`: foreground smoke/repro/quality launcher.
- `docs/REPRODUCTION_RUNBOOK.md`: detailed step-by-step reproduction process.

## Current status

Repository state is workflow-ready. Local installation and representative-workload qualification have not yet been executed on the Owner machine. No model is marked qualified and no existing platform capability has been changed.
