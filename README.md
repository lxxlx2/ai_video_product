# AI Video Product

Approved generated video deliverables are archived here by stable task name.

This repository is the canonical public product store for final approved video tasks. It is not a private training-data or persona-asset store.

## Canonical V0.2 task layout

```text
<task-slug>/
  README.md
  source/
    presentation.pptx      optional
    script.txt             optional Owner-provided source
    links.json             optional Owner-supplied requirement/reference URLs
  generated/
    requirements.md        optional
    production_brief.md    optional
    script.txt             optional generated/final script copy
    scene_plan.json        optional
    prompt_pack.json       optional
  output/
    final.mp4
  metadata/
    manifest.json
    provenance.json
    narration.json         optional
    timeline.json          optional
    publish.json
```

Older task directories using the original `source/output/metadata` layout remain valid. V0.2 adds `README.md` and `generated/` without requiring existing products to be rewritten.

## Naming rules

Each task uses one stable descriptive top-level slug.

Examples:

```text
solana-university-video-1-something-i-shipped/
solana-university-video-2-something-i-organized/
```

The approved video path is always:

```text
<task-slug>/output/final.mp4
```

A later approved revision of the same task updates `output/final.mp4`; Git history preserves older approved revisions. Do not create ad-hoc names such as `final-v2-final2.mp4`.

## Publish gate

Normal product lifecycle:

```text
local generation
  -> preview
  -> Owner approval bound to exact output hash
  -> Git LFS commit/push
  -> remote commit/output verification
  -> published
  -> eligible local duplicate/intermediate cleanup
```

A generated video is not a product release merely because it exists locally. Publishing requires explicit Owner approval of the exact candidate.

Video binaries use Git LFS.

## Provenance and generated artifacts

A task may start from uploads, public links, both, or a direct brief. When applicable, the product record may preserve safe public artifacts that explain how the result was produced:

- requirement/reference links;
- extracted requirement summary;
- production brief;
- final script;
- scene/slide plan;
- prompt pack;
- redacted model/profile/publish metadata.

These records help future agents understand the task without relying on hidden chat history.

## Privacy boundary

This repository is public. Never publish automatically:

- private voice recordings or face/persona source material;
- raw training datasets;
- private video/photo collections;
- LoRA/adapters/checkpoints intended to remain private;
- credentials, tokens, cookies, `.env` secrets or private keys;
- private runtime paths or sensitive machine metadata;
- expendable private intermediates unless explicitly approved for publication.

Private persona/training assets remain under the Owner-private local platform roots.

## Livestream clip candidate tool

[`tools/create_vertical_clip.py`](tools/create_vertical_clip.py) creates a
bounded 1080x1920 clip candidate from an explicit local video and SRT. It writes
only to the private runtime, records input and output hashes, and leaves human
approval pending. See
[`docs/livestream-vertical-slice.md`](docs/livestream-vertical-slice.md) for the
repeatable representative command and artifact contract.

## Local retention

Large local WAV/PNG/PDF/segment/render intermediates may be removed only after successful remote publish verification. Small durable job/audit records should remain locally according to platform retention policy. Source material is retained by default unless the Owner explicitly approves a different retention policy.
