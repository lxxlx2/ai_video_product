# Codex-led Local Music Orchestration

Status: TARGET ARCHITECTURE / BLOCKED ON CODEX WEB BRIDGE RELEASE READINESS

## Goal

The desired steady-state workflow is Owner approval only.

```text
Owner brief
  -> Codex discusses concept and lyrics with Owner
  -> Codex writes the final lyrics/style/job specification
  -> Codex starts or calls the local ACE-Step service
  -> Codex generates and evaluates candidates
  -> Codex performs targeted repaint/edit passes when useful
  -> Codex presents a small set of reviewable results
  -> Owner approves one exact candidate
  -> Codex promotes that exact audio as the final local artifact
  -> Codex commits the same final audio to Git LFS and pushes it
  -> Codex verifies the remote object
  -> Codex deletes task-specific intermediates
```

The Owner should not need to operate the ACE-Step UI for normal jobs after this path is implemented and qualified.

## Execution boundary

`codex-web-bridge` supplies model inference transport for Codex Desktop / CLI. Local execution remains in the Codex client. ACE-Step does not need to be embedded into the bridge.

The intended call path is:

```text
Codex Desktop / CLI
  -> local shell / Python / curl tool execution
  -> ACE-Step REST API on localhost
  -> local music runtime and model weights
```

This keeps the music integration independent from bridge protocol internals. A working Codex Web Bridge can therefore orchestrate music through ordinary local tool execution once standalone release acceptance is complete.

## Current bridge dependency

At the time this document was added, `lxxlx2/codex-web-bridge` reports:

```text
S1 dependency audit       PASS / CLOSED
S2 standalone extraction  PASS / CLOSED
S3 CLI/Desktop parity     CURRENT
S4 first release          PENDING
```

Do not add music-specific code to the bridge while S3/S4 are still being stabilized. The music repository should expose scripts and an API contract that Codex can call later without requiring bridge changes.

## Music job contract

A normal original-song job can be represented transiently as:

```json
{
  "title": "song title",
  "mode": "text2music",
  "language": "zh",
  "lyrics": "final reviewed lyrics",
  "prompt": "final reviewed style prompt",
  "duration": 240,
  "bpm": 68,
  "key_scale": "G minor",
  "time_signature": "4",
  "model": "acestep-v15-xl-sft",
  "lm_model": "acestep-5Hz-lm-4B",
  "audio_format": "wav",
  "candidate_count": 4
}
```

The job specification is working state. It may be deleted after final publication unless the Owner explicitly asks to retain it.

A reference-reproduction job additionally carries a temporary reference audio path, reference SHA-256, task type `cover` or `repaint`, and cover/repaint parameters.

## Candidate loop

Codex should keep candidate generation bounded and reviewable.

Recommended default:

```text
first pass: 4 serial candidates
  -> automatic technical checks
  -> keep best 2 for Owner review
  -> Owner may approve one or request a change
  -> repaint or regenerate only when requested or clearly needed
```

Automatic checks may include file validity, duration, clipping/silence anomalies, lyric completeness where measurable, requested language, and model/API success. Subjective musical approval always remains with the Owner.

## Approval gate

Promotion requires approval bound to an exact candidate SHA-256.

After approval, Codex must:

1. verify the candidate hash still matches;
2. copy or rename it to the canonical final local path;
3. copy the exact same bytes to the product repository final path;
4. confirm both copies have the same SHA-256;
5. commit the repository copy through Git LFS;
6. push and verify the remote commit/LFS object;
7. only then clean task-specific intermediates.

No generated candidate may silently replace an already approved final artifact without a new Owner approval.

## Final retention contract

For each completed song, the target is exactly one durable local product copy and one durable Git product copy containing the same approved audio bytes.

Suggested locations:

```text
local:
~/AI/final/music/<song-slug>/final.wav

Git:
<song-task>/output/final.wav
```

Git repository infrastructure such as shared scripts, generic runbooks and workflow documentation remains. Per-song working candidates, temporary prompts, temporary converted references, stems, repaint fragments, logs and analysis caches are deleted after remote verification.

Model weights and the ACE-Step runtime are shared capability assets and remain installed while local music creation is in use.

## Original-song workflow

The steady-state path should support a Suno-like experience through conversation:

```text
Owner describes theme
  -> Codex proposes and revises lyrics
  -> Owner approves lyrics/direction
  -> Codex creates style + structured job
  -> ACE-Step text2music
  -> candidate loop
  -> Owner approval
  -> finalization + Git + cleanup
```

The Owner does not need to provide a reference song.

## Reference workflow

For reproduction or style transfer:

```text
Owner provides reference
  -> Codex verifies reference hash
  -> Codex calls ACE-Step cover/reference generation
  -> strength/seed sweep as needed
  -> selective repaint
  -> Owner approval
  -> finalization + Git + cleanup
```

The reference file is temporary unless the Owner explicitly chooses to keep it.

## Implementation phases

Phase 1 is the current manual validation path: install ACE-Step, prove MLX generation, prove reference reproduction, and verify final audio handling.

Phase 2 adds a localhost REST launcher and a small job runner that can submit, poll and collect ACE-Step tasks without opening the UI.

Phase 3 connects Codex Desktop / CLI to that job runner through ordinary local tool calls after `codex-web-bridge` standalone readiness is proven.

Phase 4 adds the approval-bound finalization and verified cleanup path so normal operation reduces to conversation plus Owner approval.

## Non-goals

The music workflow does not require changes to ChatGPT Web transport, browser automation internals, Codex tool protocol, or bridge conversation continuity logic.

It also does not require legacy Qwen or other local models to remain installed or concurrently resident.