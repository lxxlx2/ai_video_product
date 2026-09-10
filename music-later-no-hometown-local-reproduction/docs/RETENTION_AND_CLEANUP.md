# Retention and Cleanup Policy

This task keeps Git as the durable store for the approved final product and lightweight reproducibility metadata. Large working artifacts remain local only while they are useful.

## Durable artifacts

Keep in Git after final approval:

- `output/final.wav` as the preferred archival master when available;
- optional `output/final.flac`, `output/final.m4a`, or `output/final.mp3` delivery copies when intentionally retained;
- final lyrics and style prompt;
- generation configuration and selected seed/parameters;
- final SHA-256 and provenance metadata;
- scripts and runbooks needed to reproduce the workflow.

Repository audio uses Git LFS.

## Temporary artifacts

Delete after the final artifact has been pushed and verified remotely:

- rejected candidate songs;
- repaint fragments;
- extracted stems used only during editing;
- converted working WAV copies;
- waveform/spectrogram/analysis caches;
- temporary metadata exports;
- task-specific logs;
- temporary downloads and scratch files;
- duplicate local copies of the final artifact once the Git-backed copy has been verified.

## Reference audio

The Suno reference file and its converted working copy are local inputs. They are never committed by default. Once local reproduction is complete and no further comparison or repaint work is planned, they may be deleted together with the other task intermediates.

If the reference is intentionally retained for later A/B testing, keep only one canonical local copy plus its SHA-256 metadata and remove duplicates.

## Model/runtime retention

ACE-Step model weights and its isolated runtime are shared capability assets, not per-song products. Keep them after this song if local music creation will continue. Remove them only when the Owner decides to retire the local music capability.

Do not delete or modify unrelated runtimes as part of this task.

## Finalization order

Use this order so cleanup never destroys the only good copy:

```text
select final candidate
-> compute SHA-256
-> copy/rename to output/final.<format>
-> commit through Git LFS
-> push
-> verify remote commit and LFS object
-> verify final audio can be retrieved/opened
-> delete local candidates/intermediates/reference working copies
-> keep only shared model/runtime if future music work is planned
```

Cleanup is intentionally after remote verification. Do not delete intermediates before the final artifact is confirmed durable.
