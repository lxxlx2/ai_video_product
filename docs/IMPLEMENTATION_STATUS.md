# AI 内容生产平台实施状态

更新时间：2026-09-15  
当前分支：`feat/local-music-reproduction-v01`

## 当前阶段

```text
Phase 0 文档和契约        PASS
Phase 1 服务层稳定        PASS
Phase 2 分析和短实验      IN PROGRESS
Phase 3 完整生成          PENDING
Phase 4 发布和清理        PENDING
Phase 5 共享化和迁移      PENDING
Phase 6 Codex 接管        PENDING
```

## Phase 0

已完成：

```text
docs/PRODUCT_REQUIREMENTS.md
docs/TECHNICAL_DESIGN.md
docs/TECHNICAL_IMPLEMENTATION_PLAN.md
docs/REPOSITORY_STRUCTURE.md
docs/PRODUCT_WORKFLOW.md
```

## Phase 1 / T1 服务层稳定

状态：`PASS`

READY Gate：

```text
models_initialized=true
llm_initialized=true
loaded_model=acestep-v15-xl-sft
loaded_lm_model=acestep-5Hz-lm-4B
```

2026-09-13 本机验收通过：

```text
READY
stop
DOWN
ensure from DOWN
READY_REUSED=false
ensure while READY
READY_REUSED=true
T1_SERVICE_ACCEPTANCE_PASS
```

## Phase 2 / T2 参考音频深度分析

状态：`PASS`

实现：

```text
music-later-no-hometown-local-reproduction/scripts/reference_analysis.py
music-later-no-hometown-local-reproduction/scripts/run_reference_analysis.sh
music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh
music-later-no-hometown-local-reproduction/jobs/reference-analysis.json
music-later-no-hometown-local-reproduction/docs/REFERENCE_ANALYSIS_OPERATIONS.md
```

固定 ACE-Step commit：

```text
ca1e85fe9430179831e6bc6be790c332190a3866
```

参考工作 WAV SHA256：

```text
288edd5197a7535d9dadfac27dc1aea469999e16dc6dfeaf1291cc882afd6775
```

音频通过 `multipart/form-data` 的 `src_audio` 字段上传到本机 `127.0.0.1` ACE-Step API，规避上游对任意绝对音频路径的安全限制。

2026-09-15 模型分析成功：

```text
task_id=09121dc7-e44b-4169-9eee-0bae68b1dd01
status=1
status_message=Full Hardware Analysis Success
bpm=130
keyscale=B♭ major
timesignature=4
duration=336
genre=Chinese folk-pop
language=zh
audio_codes_length=33160
metas_present=true
audio_codes_present=true
```

4B LM 的歌词识别存在明显错误和 audio code token 混入，因此后续生成继续使用项目中人工确认的歌词。BPM、Key、结构、风格描述和 audio codes 作为技术参考。

T2 过程中完成了三类兼容修复：

```text
绝对音频路径 -> multipart 本机上传
*.log ignore -> 固定 allowlist + 精确 git add -f
transport.type 验收 -> 兼容实际 transport.content_type
```

最终本机验收：

```text
LOCAL_ANALYSIS_VALID=true
TASK_ID=09121dc7-e44b-4169-9eee-0bae68b1dd01
BPM=130
KEYSCALE=B♭ major
TIMESIGNATURE=4
DURATION=336
LANGUAGE=zh
AUDIO_CODES_LENGTH=33160
TRANSPORT=multipart/form-data
AUDIO_FIELD=src_audio
REMOTE_ANALYSIS_VERIFIED=true
REMOTE_LOG_VERIFIED=true
T2_REFERENCE_ANALYSIS_ACCEPTANCE_PASS
```

## Phase 2 / T3 参考歌曲短片段准备

状态：`IMPLEMENTED, WAITING LOCAL ACCEPTANCE`

实现：

```text
music-later-no-hometown-local-reproduction/jobs/reference-clip.json
music-later-no-hometown-local-reproduction/scripts/prepare_reference_clip.py
music-later-no-hometown-local-reproduction/scripts/run_reference_clip_prepare.sh
music-later-no-hometown-local-reproduction/scripts/accept_reference_clip_prepare.sh
music-later-no-hometown-local-reproduction/docs/REFERENCE_CLIP_OPERATIONS.md
```

T3 目标：

```text
验证完整参考 WAV SHA256
读取已通过的 T2 分析结果
使用 ffmpeg 生成低采样率技术代理
扫描候选窗口
自动选出 3 个 32 秒代表性片段
WAV 只保存在本机 private 目录
Git 只发布 selection metadata
```

当前选择策略：

```text
energy_transition_v1
45% transition rise
25% activity
20% stability
10% center bias
```

本地候选目录：

```text
~/AI/private/music-source/later-no-hometown/clips/
```

Git 输出：

```text
music-later-no-hometown-local-reproduction/metadata/reference-clip.latest.json
```

正常验收：

```bash
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_clip_prepare.sh
```

通过标志：

```text
REFERENCE_CLIP_PREPARE_PASS
REFERENCE_CLIP_PUBLISHED
LOCAL_REFERENCE_CLIPS_VALID=true
REMOTE_CLIP_METADATA_VERIFIED=true
T3_REFERENCE_CLIP_ACCEPTANCE_PASS
```

T3 通过后进入：

```text
T4 experiment job
T5 short cover experiment
```

## 后续顺序

```text
T1 music API service               PASS
T2 reference analysis              PASS
T3 clip prepare                    WAITING LOCAL ACCEPTANCE
T4 experiment job                 PENDING
T5 short cover experiment         PENDING
T6 review auto publish            PENDING
T7 full song runner               PENDING
T8 finalize                       PENDING
T9 cleanup                        PENDING
T10 shared/music extraction       PENDING
T11 products directory migration  PENDING
T12 Codex takeover                PENDING
```
