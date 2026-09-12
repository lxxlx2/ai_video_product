# Output gate

Generated candidates stay local during experimentation, normally under:

```text
~/AI/runtime/music/output/later-no-hometown/
```

Do not commit candidate WAV/FLAC/M4A/MP3 files, stems, repaint fragments, logs, temporary analysis files, or model caches.

After the Owner selects the final candidate, copy only the approved deliverable into this directory using a stable name. Preferred archival master:

```text
final.wav
```

Optional delivery formats are also supported when useful:

```text
final.flac
final.m4a
final.mp3
```

All approved audio formats are tracked through Git LFS by the repository-level `.gitattributes`.

Before publishing, record the exact SHA-256 and generation parameters in metadata. After the remote Git push is verified and the final audio is confirmed readable from the repository, local candidates and task-specific intermediates should be deleted according to `../docs/RETENTION_AND_CLEANUP.md`.
