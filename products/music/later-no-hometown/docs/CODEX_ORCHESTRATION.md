# Codex-led Local Music Orchestration

Status: TARGET ARCHITECTURE / MUSIC API LAYER PLANNED / FULL CODEX LOOP BLOCKED ON CODEX WEB BRIDGE RELEASE READINESS

## Goal

The desired steady-state workflow is Owner approval only.

```text
Owner brief
  -> Codex discusses concept and lyrics with Owner
  -> Codex writes the approved lyrics, style, and structured job specification
  -> Codex starts or verifies the local ACE-Step REST service
  -> Codex submits the generation job
  -> Codex polls and collects candidates
  -> Codex performs deterministic technical checks
  -> Codex optionally runs bounded strength/seed sweeps
  -> Codex performs targeted repaint/edit passes when useful
  -> Codex presents a small review set
  -> Owner approves one exact candidate
  -> Codex promotes that exact audio as the final local artifact
  -> Codex commits the identical final audio to Git LFS and pushes it
  -> Codex verifies the remote commit and LFS object
  -> Codex deletes task-specific intermediates
```

The Owner should not need to operate the ACE-Step UI for normal jobs after the API path is implemented and qualified.

## Execution boundary

`codex-web-bridge` supplies inference transport for Codex Desktop / CLI. Local execution remains in the Codex client.

ACE-Step must stay independent from bridge protocol internals.

Intended call path:

```text
Codex Desktop / CLI
  -> local shell / Python execution
  -> repository music runner
  -> ACE-Step REST API on 127.0.0.1:8001
  -> local ACE-Step runtime and model weights
```

This means the bridge does not need music-specific protocol changes. Once Codex standalone execution is accepted, it can orchestrate music through ordinary local tools.

## Current bridge dependency

Do not add ACE-Step generation logic into `codex-web-bridge` while standalone bridge work is still being stabilized.

The music side should expose a stable script/API contract that Codex can call later without bridge changes.

## Current music-side state

As of 2026-09-12:

```text
ACE-Step quality runtime installed              PASS
acestep-v15-xl-sft on MLX                       PASS
acestep-5Hz-lm-4B on MLX                        PASS
30 second text-to-music generation              PASS
first full 5:36 reference Remix                 IN PROGRESS
REST production runner                          PLANNED NEXT
approval-bound finalization                      PENDING
Codex fully autonomous operation                 PENDING BRIDGE READINESS
```

The first short generation proved the stack works technically. It also exposed an important control issue: automatic LM metadata planning selected `G major` despite a melancholic minor-key prompt. For tightly controlled reference reproduction, source audio and explicit metadata should dominate the first pass.

Current detailed evidence is in `PROGRESS_2026-09-12.md`.

## UI policy

Gradio is retained for:

```text
manual debugging
exploratory parameter discovery
visual inspection during early development
```

Normal production should use the REST API.

Rationale:

```text
UI state is harder to reproduce
manual copy/paste is error-prone
file upload state is awkward for Codex
seed and parameter provenance is weaker
result collection and cleanup require extra manual steps
```

## REST production contract

ACE-Step exposes an asynchronous localhost workflow:

```text
POST /release_task
  -> task_id

POST /query_result
  -> 0 queued/running
  -> 1 succeeded
  -> 2 failed

GET /v1/audio?path=...
  -> audio result when needed
```

The detailed implementation plan lives in `API_AUTOMATION_PLAN.md`.

## Music job contract

A normal original-song job should be represented as a checked or transient JSON spec.

Example:

```json
{
  "schema_version": 1,
  "title": "song title",
  "slug": "song-slug",
  "task_type": "text2music",
  "language": "zh",
  "prompt_file": "generated/style.txt",
  "lyrics_file": "generated/lyrics.txt",
  "audio_duration": 240,
  "bpm": 68,
  "key_scale": "G minor",
  "time_signature": "4",
  "model": "acestep-v15-xl-sft",
  "lm_model_path": "acestep-5Hz-lm-4B",
  "lm_backend": "mlx",
  "thinking": true,
  "audio_format": "wav",
  "candidate_count": 1
}
```

A reference-reproduction job additionally carries:

```text
src_audio_path or reference_audio_path
source SHA-256
task_type cover/repaint
cover/repaint strength
explicit source duration
```

Long lyrics and style prompts should live in text files. JSON should reference them so the creative text has a clean diff history.

## Reference reproduction defaults

For the current quality path:

```text
model: acestep-v15-xl-sft
LM available: acestep-5Hz-lm-4B
backend: mlx
batch_size: 1
inference_steps: 50
infer_method: ode
vocal_language: zh
audio_format: wav
```

For the first source-constrained reproduction pass:

```text
thinking: false
```

This prevents the LM from freely recomposing semantic audio codes when the source audio is intended to provide melody, harmony, timing, and structure.

After the source-guided baseline works, explicit experiments can re-enable selected LM behavior if useful.

## Candidate loop

Candidate generation must stay bounded and reviewable.

Recommended control loop:

```text
1 baseline candidate
  -> Owner review
  -> one parameter change
  -> Owner review
  -> find a useful strength range
  -> test a small seed set
  -> retain at most 2 or 3 serious review candidates
  -> repaint localized defects
```

Do not default to four or eight expensive full-song generations before learning from the first result.

Automatic checks may include:

```text
file validity
duration tolerance
sample rate/channels readable
silence anomalies
clipping/peak sanity
requested language where measurable
source/reference SHA-256
output SHA-256
API terminal success
```

Subjective musical approval remains with the Owner.

## Candidate manifest

Every review candidate should be attributable to exact execution state.

Suggested manifest:

```json
{
  "task_id": "...",
  "candidate_id": "...",
  "created_at": "...",
  "model": "acestep-v15-xl-sft",
  "seed": 123456,
  "params": {},
  "source_sha256": "...",
  "output_sha256": "...",
  "duration_seconds": 335.84,
  "technical_checks": {},
  "review_state": "pending"
}
```

## Approval gate

Promotion requires approval bound to an exact candidate SHA-256.

After approval, Codex must:

1. recompute and verify the candidate hash;
2. copy or rename it to the canonical final local path;
3. copy the exact same bytes to the product repository final path;
4. confirm local and repository hashes match;
5. commit the repository copy through Git LFS;
6. push and verify the remote commit/LFS object;
7. only then clean task-specific intermediates.

If the candidate bytes change after approval, finalization must stop and require new approval.

## Final retention contract

For each completed song, keep one durable local product copy and one durable Git product copy containing the same approved audio bytes.

Suggested locations:

```text
local:
~/AI/final/music/<song-slug>/final.wav

Git:
<song-task>/output/final.wav
```

Durable repository infrastructure may include:

```text
generic runner scripts
runbooks
architecture documentation
lightweight reproducibility metadata
```

Delete task-specific working candidates, temporary prompts, temporary converted references, stems, repaint fragments, logs, runtime JSON, and analysis caches after remote verification unless the Owner explicitly requests retention.

Model weights and the ACE-Step runtime are shared capability assets and remain installed while local music creation is in use.

## Original-song workflow

The steady-state path should support a Suno-like experience through conversation:

```text
Owner describes theme
  -> Codex proposes/revises lyrics and direction
  -> Owner approves creative direction
  -> Codex creates style + structured job
  -> ACE-Step text2music through REST
  -> bounded candidate loop
  -> Owner approval
  -> finalization + Git + cleanup
```

Original creation can use `thinking=true` when LM composition planning is desirable. Effective LM metadata must be recorded so successful results can be reproduced.

## Reference workflow

For reproduction or style transfer:

```text
Owner provides reference
  -> Codex verifies reference hash
  -> Codex uses local absolute source path
  -> ACE-Step cover/reference generation through REST
  -> bounded strength/seed tuning
  -> selective repaint
  -> Owner approval
  -> finalization + Git + cleanup
```

The reference file is temporary unless the Owner explicitly chooses to keep it.

## Planned local tool interface

The expected repository-level interface is:

```text
scripts/music_api_start.sh
scripts/music_api_health.sh
scripts/music_run.py
scripts/music_finalize.py
scripts/music_cleanup.py
```

The main runner should eventually expose:

```text
music_run.py validate <job.json>
music_run.py submit <job.json>
music_run.py status <task-id>
music_run.py collect <task-id>
music_run.py finalize <candidate> --approved-sha256 <sha>
music_run.py cleanup <task-id>
```

Codex should call these tools instead of driving the browser.

## Implementation phases

### Phase 1: manual truth-finding

Current phase.

Completed:

```text
installation
model validation
short generation
cleanup validation
```

Still required:

```text
finish first full reference Remix
review actual similarity/failure modes
record exact successful baseline parameters
```

### Phase 2: REST parity

Implement localhost REST startup, health, submit, poll, and collect.

Goal:

```text
reproduce the same baseline job without Gradio
```

### Phase 3: bounded candidate automation

Add controlled strength/seed sweeps, manifests, technical checks, and review set preparation.

### Phase 4: approval-bound finalization

Add exact-hash approval, local final promotion, Git LFS copy, push verification, and safe cleanup.

### Phase 5: Codex orchestration

After `codex-web-bridge` standalone readiness is proven, Codex owns the operational loop through normal local shell/tool calls.

Owner interaction reduces to:

```text
creative discussion
listen/review
approve or request change
```

## Failure policy

The music runner must fail closed on:

```text
reference hash mismatch
missing source file
API unhealthy
unexpected port owner
requested model unavailable
invalid or missing audio output
candidate hash changed after approval
Git or LFS verification failure
```

It must not:

```text
kill unrelated processes
delete shared model assets
silently switch to paid/cloud services
publish an unapproved candidate
```

## Non-goals

The music workflow does not require changes to ChatGPT Web transport, browser automation internals, Codex tool protocol, or bridge conversation continuity logic.

It also does not require legacy Qwen or other local models to remain installed or concurrently resident.
