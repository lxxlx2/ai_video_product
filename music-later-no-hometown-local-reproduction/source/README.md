# Local source media

The selected reference audio for this task stays on the Owner machine and is not committed to this public repository.

Expected file:

```text
后来没有故乡.m4a
```

Expected SHA-256:

```text
176c81b30cbd68de6cd7c900d1513160f9a6a591eb7e9bed65d848f273c48b0e
```

Use:

```bash
bash ../scripts/prepare_reference.sh "/absolute/path/to/后来没有故乡.m4a"
```

The preparation script verifies the hash, records ffprobe metadata, and creates a 48 kHz stereo WAV working copy under the private local music source root.

Do not copy reference audio, stems, or derived private working files into this public task directory unless the Owner explicitly approves publication of that exact media.
