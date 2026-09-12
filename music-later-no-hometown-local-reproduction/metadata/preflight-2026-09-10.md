# Local Music Preflight Evidence

Date: 2026-09-10
Host: jerson的MacBook Pro
OS: macOS 26.6.2
Architecture: arm64
Result: PRECHECK_PASS

## Tooling

- git: /usr/bin/git
- ffmpeg: /opt/homebrew/bin/ffmpeg
- ffprobe: /opt/homebrew/bin/ffprobe
- shasum: /usr/bin/shasum
- lsof: /usr/sbin/lsof
- uv: 0.12.5, Homebrew aarch64-apple-darwin

## Resource snapshot

- Physical memory: 51,539,607,552 bytes, approximately 48 GiB
- System-wide memory free percentage reported by `memory_pressure`: 72%
- Swap total: 3072.00 MiB
- Swap used: 1413.25 MiB
- Swap free: 1658.75 MiB
- Data volume: 926 GiB total, 391 GiB used, 511 GiB available
- ACE-Step planned port 8215: free

## Interpretation

The read-only preflight completed successfully. The machine has the required command-line tooling, Apple Silicon architecture, sufficient free disk space for the planned ACE-Step runtime and model downloads, and the dedicated local service port is available.

This result authorizes proceeding to the isolated ACE-Step bootstrap for this workflow. It does not by itself prove model generation quality or final runtime performance.

No process or application was stopped by the preflight.
