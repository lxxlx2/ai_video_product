# ACE-Step REST Automation Plan

Status: PLANNED AFTER FIRST FULL MANUAL REFERENCE RUN

## Objective

Replace routine Gradio interaction with a reproducible localhost API workflow that Codex can execute end to end.

The target user experience is:

```text
Owner describes the song or asks to reproduce a reference
-> Codex discusses lyrics and direction
-> Owner approves lyrics/direction
-> Codex performs all local execution
-> Owner listens to a small review set
-> Owner approves one exact candidate
-> Codex finalizes, pushes, verifies, and cleans up
```

Gradio is retained for debugging and exploratory manual tuning. It should not be required for normal production runs.

## Why API-first

Manual UI work introduces avoidable state and makes automation fragile:

```text
hidden checkbox state
manual copy/paste
manual file upload
manual seed tracking
manual result collection
manual cleanup
```

ACE-Step 1.5 already exposes a structured REST API with the fields required by this workflow, including model selection, prompt, lyrics, language, duration, seed, source/reference audio paths, task type, cover strength, inference steps, output format, and LM controls.

For local files already present on the Mac, the API can use absolute server-local paths such as:

```text
/Users/jerson/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav
```

This avoids browser upload state.

## Runtime topology

Target process layout:

```text
Codex Desktop / CLI
  -> local shell or Python runner
  -> ACE-Step REST API
       host: 127.0.0.1
       port: 8001
       backend: MLX
  -> ACE-Step model/runtime directory
       /Users/jerson/AI/runtime/music/acestep-1.5
  -> private work area
       /Users/jerson/AI/private/music-source/
       /Users/jerson/AI/work/music/
  -> approved local product
       /Users/jerson/AI/final/music/<song-slug>/final.wav
  -> Git LFS product copy
       <song-task>/output/final.wav
```

No browser automation is required.

## API lifecycle

ACE-Step uses an asynchronous task flow:

```text
POST /release_task
  -> task_id

POST /query_result
  -> status 0 while queued/running
  -> status 1 on success
  -> status 2 on failure

GET /v1/audio?path=...
  -> result audio when needed
```

A runner should poll at a conservative interval and surface server errors verbatim.

## Required scripts

Planned repository interface:

```text
scripts/
  music_api_start.sh
  music_api_health.sh
  music_submit.py
  music_poll.py
  music_collect.py
  music_finalize.py
  music_cleanup.py
  music_run.py
```

Responsibilities:

### `music_api_start.sh`

Start ACE-Step REST API on Apple Silicon with MLX and the intended quality profile. It must bind to localhost only and must not kill unrelated processes.

Expected endpoint:

```text
http://127.0.0.1:8001
```

### `music_api_health.sh`

Read-only checks:

```text
/health
/v1/models
port owner
expected model availability
```

Fail fast if another process owns the configured port.

### `music_submit.py`

Input: validated JSON job file.

Responsibilities:

```text
validate job schema
verify local reference/source file exists
verify expected reference SHA-256 when supplied
submit POST /release_task
persist task_id and normalized effective parameters
```

### `music_poll.py`

Poll `/query_result` until terminal status. It must keep the task id and raw failure message.

### `music_collect.py`

Resolve output audio paths, download or copy the result into the task work directory, calculate SHA-256, run technical checks, and write a candidate manifest.

### `music_finalize.py`

Requires explicit approval of an exact candidate hash.

Responsibilities:

```text
recompute candidate SHA-256
confirm it matches approved SHA-256
copy exact bytes to canonical local final path
copy exact bytes to repository output/final.wav
confirm both hashes match
commit through Git LFS
push
verify remote commit/object
```

### `music_cleanup.py`

Runs only after finalization verification. Removes task-specific candidates, temporary reference conversions, generated logs, transient JSON task state, repaint fragments, and analysis caches according to retention policy.

Shared ACE-Step runtime and model weights are preserved.

### `music_run.py`

High-level orchestrator for Codex. Expected subcommands:

```text
music_run.py validate <job.json>
music_run.py submit <job.json>
music_run.py status <task-id>
music_run.py collect <task-id>
music_run.py finalize <candidate-path> --approved-sha256 <sha>
music_run.py cleanup <task-id>
```

Later it may provide a single bounded execution mode:

```text
music_run.py run <job.json>
```

This command must stop before final promotion and wait for Owner approval.

## Job specification

Jobs should be plain JSON so they can be generated, reviewed, diffed, and reproduced.

Suggested reference reproduction job:

```json
{
  "schema_version": 1,
  "title": "后来没有故乡",
  "slug": "later-no-hometown",
  "task_type": "cover",
  "model": "acestep-v15-xl-sft",
  "lm_model_path": "acestep-5Hz-lm-4B",
  "lm_backend": "mlx",
  "src_audio_path": "/Users/jerson/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav",
  "src_audio_sha256": "176c81b30cbd68de6cd7c900d1513160f9a6a591eb7e9bed65d848f273c48b0e",
  "prompt_file": "generated/style.txt",
  "lyrics_file": "generated/lyrics.txt",
  "thinking": false,
  "vocal_language": "zh",
  "audio_duration": 335.84,
  "batch_size": 1,
  "inference_steps": 50,
  "infer_method": "ode",
  "use_random_seed": true,
  "audio_cover_strength": 0.9,
  "cover_noise_strength": 0.2,
  "audio_format": "wav"
}
```

The runner should materialize file-based prompt and lyrics into the REST request. Long creative text should remain in normal text files instead of being duplicated into JSON.

## Parameter policy

For quality reference reproduction with `acestep-v15-xl-sft`:

```text
inference_steps: 50
infer_method: ode
batch_size: 1
thinking: false for source-constrained first pass
vocal_language: zh
output: wav
```

Reference strength values are experiment parameters. The first controlled sweep should change one dimension at a time.

Recommended first sweep after the current manual run establishes a baseline:

```text
cover_noise_strength: 0.15, 0.20, 0.25
```

If structural preservation remains weak, then adjust the Remix/cover preservation parameter separately. Do not sweep multiple dimensions simultaneously unless the previous dimension has been bounded.

## Metadata policy

Automatic metadata inference previously produced a `G major` plan for a prompt that requested a melancholic minor-key result. Therefore:

```text
Do not rely on LM metadata inference as the only source of truth for controlled reproduction.
```

The automation should support explicit pinned values for:

```text
bpm
key_scale
time_signature
audio_duration
vocal_language
```

If a field is intentionally left automatic, record that fact in the candidate manifest.

## Candidate manifest

Every candidate worth retaining for review gets a machine-readable manifest:

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

Only the manifest for actively reviewed candidates must survive during a task. After final publication, durable metadata should be minimized to what is useful for reproducibility and audit.

## Technical checks

Before presenting a candidate, automate inexpensive deterministic checks:

```text
file exists and nonzero
ffprobe succeeds
duration within configured tolerance
sample rate and channels readable
no all-silence output
peak is finite
SHA-256 recorded
source/reference hash still matches
API task ended with success
```

Optional later checks:

```text
lyrics transcription coverage
clipping ratio
long silence anomalies
section timing comparison
reference similarity metrics
```

Subjective musical quality remains an Owner decision.

## Candidate strategy

Avoid uncontrolled batch explosion.

Default production loop:

```text
1 baseline candidate
-> review
-> one controlled parameter change if needed
-> review
-> once a good parameter region is found, test a small seed set
-> keep at most 2 or 3 serious review candidates
-> use repaint for local defects
```

This reduces storage, compute, and review fatigue.

## Original song mode

The same runner must support fully original text-to-music creation.

Example path:

```text
Owner concept
-> Codex drafts lyrics and style
-> Owner approves or requests edits
-> task_type=text2music
-> Codex submits controlled candidates
-> Owner reviews
-> finalization gate
```

Original song creation may use `thinking=true` where the 5Hz LM's composition planning is helpful. The runner must record the LM-generated metadata and effective parameters so successful ideas can be reproduced.

## Reference mode

For reproduction:

```text
source/reference audio drives structure
thinking defaults off for the first controlled pass
explicit lyrics and prompt are supplied
strength and seed sweeps are bounded
repaint is preferred over whole-song regeneration when only a local region is bad
```

## Codex integration boundary

`codex-web-bridge` should not contain ACE-Step-specific generation logic.

After standalone bridge readiness, Codex only needs ordinary local tool access to:

```text
read/write the song task repository
execute the runner
inspect manifests and logs
play or surface output paths for Owner review
run Git operations
```

The music API remains an independent localhost service.

## Approval contract

No script may automatically publish a final candidate based only on a score.

Finalization requires an Owner-approved exact SHA-256. If bytes change after approval, finalization must fail and require a new approval.

## Retention contract

Long-term durable assets per completed song:

```text
local approved audio:
/Users/jerson/AI/final/music/<song-slug>/final.wav

Git approved audio:
<song-task>/output/final.wav

lightweight documentation and reproducibility metadata as needed
```

Delete after verified publication:

```text
rejected candidates
temporary WAV conversions
stems not explicitly retained
repaint fragments
job runtime files
task logs
analysis caches
browser/Gradio exports
```

Keep shared capability assets:

```text
ACE-Step runtime
model weights
generic scripts
documentation
```

## Implementation phases

### Phase A: finish manual truth-finding

Current phase.

Acceptance:

```text
one full 5:36 Remix/Cover candidate completes
Owner evaluates actual similarity and failure modes
exact effective parameters are recorded
```

### Phase B: REST parity

Implement API launcher and runner. Reproduce the same manual settings through REST and confirm output generation works without opening Gradio.

Acceptance:

```text
health check passes
job submission works
polling works
WAV collection works
same quality model is used
reference hash is verified
```

### Phase C: bounded candidate automation

Add parameter sweeps, technical checks, candidate manifests, and review set preparation.

Acceptance:

```text
Codex can generate a small bounded candidate set without UI interaction
all candidates are attributable to exact parameters and hashes
```

### Phase D: approval-bound publication

Add finalization, Git LFS push, remote verification, and cleanup.

Acceptance:

```text
Owner approval references exact SHA-256
local final and Git final bytes match
remote Git/LFS object verified
intermediates removed only after verification
```

### Phase E: Codex full orchestration

After `codex-web-bridge` release readiness, Codex owns the operational loop. Owner interaction is limited to creative discussion and approval.

## Failure policy

The runner must fail closed on:

```text
reference hash mismatch
missing source file
wrong model unavailable
API unhealthy
unexpected port owner
output missing
invalid audio
candidate hash changed after approval
Git/LFS verification failure
```

It must not kill unrelated processes, delete model assets, or silently fall back to cloud/paid services.

## Next implementation task

After the current manual full-song run finishes and its result is reviewed:

```text
implement music_api_start.sh
implement music_api_health.sh
implement music_run.py validate/submit/status/collect
add one checked-in example job for later-no-hometown
prove REST parity with one full reference candidate
```
