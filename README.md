# AI Video Product

Approved generated media deliverables are archived here by stable task name.

This repository remains the canonical public product store for approved video tasks and now also supports explicitly approved audio/music tasks. Existing video directories and the V0.2 contract remain valid. The repository is not a private training-data, persona-asset, or raw reference-media store.

## Canonical V0.3 task layout

Video tasks may keep the existing V0.2 layout:

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
    scene_plan.json         optional
    prompt_pack.json        optional
  output/
    final.mp4
  metadata/
    manifest.json
    provenance.json
    narration.json         optional
    timeline.json          optional
    publish.json
```

Audio/music workflows use the same lifecycle with media-specific files:

```text
<task-slug>/
  README.md
  source/
    README.md               public instructions only; private reference audio stays local
  generated/
    lyrics.txt              optional approved lyrics/prompt material
    style.txt               optional generation style/prompt
  config/
    reproduction.json       versioned non-secret workflow configuration
  docs/
    REPRODUCTION_RUNBOOK.md
  scripts/
    preflight_macos.sh
    bootstrap_acestep_macos.sh
    prepare_reference.sh
    launch_acestep_macos.sh
  metadata/
    reference.json          safe source hash/technical metadata only
  output/
    final.wav               only after explicit Owner publication approval
```

Older task directories using the original `source/output/metadata` layout remain valid. V0.3 adds an audio extension without requiring existing products to be rewritten.

## Naming rules

Each task uses one stable descriptive top-level slug.

Examples:

```text
solana-university-video-1-something-i-shipped/
solana-university-video-2-something-i-organized/
music-later-no-hometown-local-reproduction/
```

For video, the approved path remains:

```text
<task-slug>/output/final.mp4
```

For audio, an approved master may use:

```text
<task-slug>/output/final.wav
```

Git history preserves approved revisions. Do not create ad-hoc names such as `final-v2-final2.*`.

## Publish gate

Normal product lifecycle:

```text
local generation
  -> preview
  -> Owner approval bound to exact output hash
  -> Git/LFS commit and push when publication is approved
  -> remote commit/output verification
  -> published
  -> eligible local duplicate/intermediate cleanup
```

A generated video or song is not a product release merely because it exists locally. Publishing requires explicit Owner approval of the exact candidate.

Large approved media binaries should use Git LFS.

## Local-reference rule for music

Reference audio used for cover, reproduction, stem separation, voice/style guidance, or repainting stays outside this public repository by default. Commit only safe metadata such as filename, codec, duration, sample rate, hash, prompt/configuration, and reproducibility notes.

Do not upload a private or third-party source track merely to make the workflow reproducible. The local workflow should verify the source by SHA-256 and operate from an Owner-private media root.

## Provenance and generated artifacts

A task may start from uploads, public links, both, or a direct brief. When applicable, the product record may preserve safe public artifacts that explain how the result was produced:

- requirement/reference links;
- extracted requirement summary;
- production brief;
- final script or approved lyrics;
- scene/slide plan;
- prompt pack/style prompt;
- redacted model/profile/publish metadata;
- safe source-media hashes and technical properties.

These records help future agents understand the task without relying on hidden chat history.

## Privacy boundary

This repository is public. Never publish automatically:

- private voice recordings or face/persona source material;
- raw music reference audio or stems unless explicitly approved;
- raw training datasets;
- private video/photo collections;
- LoRA/adapters/checkpoints intended to remain private;
- credentials, tokens, cookies, `.env` secrets or private keys;
- private runtime paths when they expose sensitive information beyond documented platform defaults;
- expendable private intermediates unless explicitly approved for publication.

Private persona, training, and reference-media assets remain under Owner-private local platform roots.

## Local retention

Large local WAV/PNG/PDF/segment/render intermediates may be removed only after successful remote publish verification or explicit Owner cleanup approval. Small durable job/audit records should remain locally according to platform retention policy. Source material is retained by default unless the Owner explicitly approves a different retention policy.
