# Livestream vertical clip candidate

`tools/create_vertical_clip.py` turns an explicit local video and SRT into a
private 1080x1920 candidate. It centers the landscape source over a blurred
portrait background, keeps audio, and delivers subtitles as both an MP4
`mov_text` track and a sidecar SRT.

The command requires exact input SHA-256 values and refuses overwrites. Output
is restricted to `/Users/jerson/AI/runtime/livestream-clips/<run-id>` and is
assembled in a private staging directory before an atomic rename. Every result
contains `approval.json` with `status: pending` and `publish_allowed: false`.
The tool has no network, upload, or publish implementation.

## Representative run

The current local representative source has a complete 20.390-second segment
covering three steps for a student build session and the organizer's role in
removing friction:

```bash
python3 tools/create_vertical_clip.py create \
  --source-video /Users/jerson/AI/runtime/presentation-jobs/solana-video-2-final/output/presentation.mp4 \
  --source-srt /Users/jerson/AI/runtime/presentation-jobs/solana-video-2-final/output/presentation.srt \
  --expected-video-sha256 ad508a8f0e7519124c28888b3a4a97dae6c397bed7921ddc3636c44a7b956f7e \
  --expected-srt-sha256 a51d4ed9a3eed8fd2c715e00952ad8f8794b0d753a4590dbd6f6c10c3c07d331 \
  --start 22.530 \
  --end 42.920 \
  --run-id student-builder-three-steps-YYYYMMDDTHHMMSSZ \
  --title '把学生从“想学 AI”带到能做 Demo，只要这 3 步' \
  --caption '定义真实用户问题 → 做最小可演示版本 → 用 1 分钟讲清楚。组织者真正要做的，是把每一步的阻力降下来。#AI实践 #学生创业 #BuildInPublic'
```

Use a new run ID for each candidate. Verify a persisted result without changing
it:

```bash
python3 tools/create_vertical_clip.py verify \
  --artifact /Users/jerson/AI/runtime/livestream-clips/<run-id>
```

The output directory contains:

```text
vertical.mp4
clip.srt
title.txt
caption.txt
manifest.json
approval.json
```

`manifest.json` records the source hashes, selected timestamps, exact FFmpeg
argument vector, media probes, output hashes, and safety state. Publication is
a separate owner-controlled action after approval of the exact video hash.
