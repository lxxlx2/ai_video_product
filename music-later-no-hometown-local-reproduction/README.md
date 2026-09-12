# 后来没有故乡 · Local Reproduction

This task records a reproducible local workflow for rebuilding the approved reference song with ACE-Step 1.5 on Apple Silicon, and serves as the first concrete local music-generation workflow for future original songs.

## Goal

Start from the Owner-selected Suno reference file and produce a close local reproduction with controllable lyrics, structure, vocal character, arrangement, seeds, and local repaint/edit passes.

The same ACE-Step runtime will later support original text/lyrics-to-song creation without requiring a Suno reference.

The target for this task is musical similarity and iterative control. Exact waveform-level duplication is not assumed.

## Current status

As of 2026-09-12:

```text
Host preflight                         PASS
ACE-Step bootstrap                    PASS
Reference verification/conversion     PASS
Quality model download                PASS
XL SFT load on MLX                    PASS
4B LM load on MLX                     PASS
30 s local generation                 PASS
Model/cache cleanup                   PASS
First full 5:36 Remix/Cover run       IN PROGRESS
REST API automation                   PLANNED NEXT
Codex full orchestration              BLOCKED ON BRIDGE READINESS
```

The quality runtime is fully installed and has already generated local audio successfully.

The current manual full-song Remix is intentionally being allowed to finish before API automation work changes the execution surface. Detailed evidence and decisions are recorded in [`docs/PROGRESS_2026-09-12.md`](docs/PROGRESS_2026-09-12.md).

## Runtime boundary

- ACE-Step lives in its own runtime directory and environment.
- The service binds to localhost only.
- The reference M4A, derived WAV, stems, model weights, caches, and unapproved output audio stay local during work.
- Scripts never kill unrelated processes or modify unrelated runtimes.
- No paid/cloud fallback is enabled.
- Current execution does not require simultaneous coexistence with older heavy-model stacks.
- Gradio is a debugging/manual tuning surface. The intended production surface is the localhost REST API.

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

Prepared local working reference:

```text
/Users/jerson/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav
```

The reference audio itself is intentionally not committed to the repository.

## Installed quality runtime

Runtime path:

```text
/Users/jerson/AI/runtime/music/acestep-1.5
```

Pinned ACE-Step commit:

```text
ca1e85fe9430179831e6bc6be790c332190a3866
```

Quality profile:

```text
DiT: acestep-v15-xl-sft
LM:  acestep-5Hz-lm-4B
backend: MLX
```

The service successfully reached:

```text
MLX model loaded successfully
5Hz LM initialized successfully
Service initialization completed successfully
```

Validated checkpoint footprint after stale partial-download cleanup:

```text
19G   acestep-v15-xl-sft
7.9G  acestep-5Hz-lm-4B
4.5G  acestep-v15-turbo
3.5G  acestep-5Hz-lm-1.7B
1.1G  Qwen3-Embedding-0.6B
337M  vae
36G   total checkpoints
```

The smaller Turbo and 1.7B assets are currently retained because upstream startup checks may request them. Removing them is a later optimization after API startup behavior is fully qualified.

## First local generation result

A 30 second Custom generation completed successfully on MLX. The stack proved end-to-end execution through LM, DiT, VAE, and audio output.

The musical result was rejected. The most important diagnostic finding was that automatic LM metadata planning selected `G major` even though the caption requested a melancholic minor-key direction.

Decision:

```text
Reference reproduction should use source audio as the main structural constraint.
Thinking should default off for the first controlled Remix/Cover pass.
Metadata should be pinned explicitly when automatic inference conflicts with the intended result.
```

See [`docs/PROGRESS_2026-09-12.md`](docs/PROGRESS_2026-09-12.md).

## Current manual reproduction pass

The first full 5:36 reference-guided Remix is running manually in Gradio to establish a trustworthy baseline before automation.

Current intent:

```text
mode: Remix
source: approved reference WAV
model: acestep-v15-xl-sft
thinking: off
language: zh
batch: 1
steps: 50
method: ode
sampler: euler
full-song duration
```

The Gradio progress ETA is treated as advisory only. Long full-song XL SFT generation can exceed the initial estimate.

Once this candidate finishes, its actual audio quality and effective parameters will define the first REST parity target.

## Production direction: API-first

Normal future use should not require manual Gradio setup.

ACE-Step already exposes a localhost asynchronous REST workflow:

```text
POST /release_task
-> task_id

POST /query_result
-> queued/running/succeeded/failed

GET /v1/audio?path=...
-> result audio when needed
```

The planned automation is documented in [`docs/API_AUTOMATION_PLAN.md`](docs/API_AUTOMATION_PLAN.md).

Target steady-state workflow:

```text
Owner request
-> Codex discusses lyrics/direction
-> Codex writes lyrics/style/job spec
-> Codex starts or verifies ACE-Step REST API
-> Codex submits/polls/collects candidates
-> Codex performs technical checks
-> Owner reviews a small bounded candidate set
-> Owner approves one exact candidate
-> Codex finalizes identical local + Git copies
-> Git LFS push and remote verification
-> Codex deletes task intermediates
```

The Owner should only need to participate in creative discussion and final approval.

## First deployment commands

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
bash scripts/launch_acestep_macos.sh quality
```

Gradio manual validation endpoint:

```text
http://127.0.0.1:8215
```

Future REST production endpoint is expected to use:

```text
http://127.0.0.1:8001
```

## Reproduction sequence

Use [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md) for the manual baseline process.

High-level sequence:

1. verify source hash and prepare the 48 kHz working WAV;
2. start the intended quality profile;
3. establish one valid reference-guided full-song baseline;
4. record exact parameters and output hash;
5. adjust one strength dimension at a time;
6. choose a promising seed/parameter region;
7. use Repaint only for localized defects;
8. present a small bounded review set;
9. bind Owner approval to an exact candidate SHA-256;
10. publish only the approved final artifact and lightweight metadata;
11. verify Git/LFS remotely;
12. delete task intermediates.

## Profiles

| Profile | DiT | LM | Purpose |
|---|---|---|---|
| `smoke` | `acestep-v15-turbo` | `acestep-5Hz-lm-0.6B` | optional lightweight runtime proof |
| `repro` | `acestep-v15-xl-turbo` | `acestep-5Hz-lm-1.7B` | faster reference/remix attempts |
| `quality` | `acestep-v15-xl-sft` | `acestep-5Hz-lm-4B` | preferred high-quality local creation/reproduction profile |

Current work uses `quality`.

## Git audio policy

Git can store the final approved audio. This repository tracks approved audio through Git LFS for WAV, FLAC, M4A, MP3, AAC, and OGG.

Preferred final master:

```text
output/final.wav
```

Optional delivery copies may also be retained when useful.

Rejected candidates, stems, repaint fragments, temporary WAV conversions, logs, caches, and other working files stay local and are deleted after the final Git-backed artifact has been pushed and verified. See [`docs/RETENTION_AND_CLEANUP.md`](docs/RETENTION_AND_CLEANUP.md).

## Files

- `generated/lyrics.txt`: current lyrics used for local reproduction.
- `generated/style.txt`: concise style/vocal prompt.
- `config/reproduction.json`: pinned upstream revision, profiles, paths, source metadata, and reproduction targets.
- `metadata/reference.json`: safe technical source record and SHA-256.
- `metadata/preflight-2026-09-10.md`: first successful Apple Silicon preflight evidence.
- `metadata/bootstrap-2026-09-11.md`: isolated ACE-Step dependency/bootstrap evidence.
- `metadata/model-install-2026-09-12.md`: quality-model install and runtime evidence.
- `docs/PROGRESS_2026-09-12.md`: current runtime, validation, diagnosis, manual run, and acceptance gates.
- `docs/API_AUTOMATION_PLAN.md`: planned REST runner, job contract, candidate loop, finalization, and cleanup architecture.
- `docs/REPRODUCTION_RUNBOOK.md`: manual reference-reproduction process.
- `docs/RETENTION_AND_CLEANUP.md`: final-artifact retention and cleanup policy.
- `docs/CODEX_ORCHESTRATION.md`: target Codex-led workflow after bridge readiness.
- `scripts/preflight_macos.sh`: read-only host/runtime preflight.
- `scripts/bootstrap_acestep_macos.sh`: isolated pinned ACE-Step install.
- `scripts/prepare_reference.sh`: source verification and local WAV preparation.
- `scripts/launch_acestep_macos.sh`: foreground smoke/repro/quality Gradio launcher.

## Next implementation milestone

Do not interrupt the currently running full Remix merely to switch execution surfaces.

After it completes and the Owner reviews the actual audio:

```text
1. record the exact baseline candidate and SHA-256
2. implement localhost REST launcher and health checks
3. implement structured job submission/poll/collect runner
4. reproduce the manual baseline through REST
5. add bounded candidate sweeps and manifests
6. add approval-bound finalization and Git LFS verification
7. connect Codex after codex-web-bridge standalone readiness
```
