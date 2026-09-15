# Retention and Cleanup Policy

This workflow uses a final-only product policy for completed songs.

## Durable product copies

For each approved song, keep exactly one durable local product copy and one durable Git product copy containing the same approved audio bytes.

Preferred paths:

```text
local:
~/AI/final/music/<song-slug>/final.wav

Git:
<song-task>/output/final.wav
```

Both copies must have the same SHA-256 before cleanup begins. The Git copy uses Git LFS.

Shared repository infrastructure such as generic scripts, runbooks and workflow documentation remains in Git. Task-specific working artifacts do not become durable products by default.

## Temporary job artifacts

Delete after the approved final artifact has been pushed and verified remotely:

- rejected candidate songs;
- alternate seeds;
- repaint fragments;
- extracted stems;
- converted working WAV copies;
- reference audio used for a completed reproduction job, unless explicitly retained;
- task-specific lyrics/style/job JSON used only during generation;
- waveform, spectrogram and analysis caches;
- temporary metadata exports;
- task-specific logs;
- temporary downloads and scratch files;
- duplicate local copies of the final artifact.

## Reference audio

Reference audio is a temporary input by default. Keep it while comparison, cover generation or repaint work is active. After final approval and verified publication, delete it with the other task working files unless the Owner explicitly chooses to retain it.

A hash may remain in generic workflow evidence while the source audio itself is removed.

## Model/runtime retention

ACE-Step model weights and the isolated runtime are shared capability assets. They remain installed while local music creation is in use and can be removed later if the capability is retired.

They are not counted as per-song intermediates.

## Finalization order

Use this order:

```text
select candidate
-> Owner approves exact candidate
-> compute and bind SHA-256
-> write one canonical local final.wav
-> write the same bytes to Git output/final.wav
-> verify both SHA-256 values match
-> commit through Git LFS
-> push
-> verify remote commit and LFS object
-> verify final audio can be retrieved/opened
-> delete task-specific candidates, references, prompts, stems, caches and logs
```

Cleanup begins only after remote verification. This prevents deletion of the only good candidate before the final product is durable.

## Replacement of an approved final

A later revision requires a new exact candidate approval. Codex or any automation may not silently overwrite an approved final artifact and treat it as the same release.