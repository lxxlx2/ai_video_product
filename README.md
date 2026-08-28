# AI Video Product

Generated video deliverables are archived here by task name.

## Directory convention

```text
<task-name>/
  source/
    presentation.pptx
    script.txt
  output/
    final.mp4
  metadata/
    manifest.json
    timeline.json
    narration.json
```

Each task uses a stable, descriptive task directory. Revisions of the same task stay inside that task directory rather than creating unrelated top-level folders.

Examples:

```text
solana-university-video-1-something-i-shipped/
solana-university-video-2-something-i-organized/
```

The local generation pipeline may keep large intermediate WAV, PNG, PDF, and segment files under `/Users/jerson/AI/runtime/`; only source materials, selected metadata, and final deliverables should be pushed here.
