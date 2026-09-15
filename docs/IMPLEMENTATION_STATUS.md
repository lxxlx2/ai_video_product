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

状态：`ANALYSIS + PUBLICATION PASS, WAITING VERIFY-ONLY ACCEPTANCE`

实现：

```text
music-later-no-hometown-local-reproduction/scripts/reference_analysis.py
music-later-no-hometown-local-reproduction/scripts/run_reference_analysis.sh
music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh
music-later-no-hometown-local-reproduction/jobs/reference-analysis.json
music-later-no-hometown-local-reproduction/docs/REFERENCE_ANALYSIS_OPERATIONS.md
```

### T2 第一次验收

提交阶段失败：

```text
ERROR_CODE=API_SUBMIT_FAILED
HTTP 400 Bad Request
{"detail":"absolute audio file paths are not allowed"}
```

固定 ACE-Step commit 会拒绝系统临时目录之外的绝对音频路径。参考音频及后续本地音频输入已统一改成 multipart 文件上传。

### T2 第二次验收

2026-09-15 模型分析成功：

```text
transport=multipart/form-data
audio_field=src_audio
task_id=09121dc7-e44b-4169-9eee-0bae68b1dd01
status=0
status=1
REFERENCE_ANALYSIS_PASS
```

参考分析摘要：

```text
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

4B LM 参考描述包含：

```text
clean fingerpicked acoustic guitar
warm conversational male vocal
subtle bass guitar
light steady drum beat
heartfelt spoken-word section
tender piano ending over fading acoustic guitar
```

模型转写歌词存在明显错识别，因此后续只把 BPM、Key、结构、配器、音色和 audio_codes 作为分析线索，正式歌词继续使用项目内人工确认版本。

### T2 Git 发布

第一次发布受到任务级 `.gitignore` 的 `*.log` 规则影响，已修复 allowlist 和 `git add -f`。

2026-09-15 已成功发布：

```text
REFERENCE_ANALYSIS_PUBLISHED
PUBLISHED_COMMIT=a527bb4eb1df0c5d70df72212e29c694ce2d41c0
```

远端已经包含：

```text
metadata/reference-analysis.latest.json
metadata/reference-analysis.latest.log
```

### T2 验收脚本字段兼容修复

发布成功后，本地验收脚本误读 `transport` schema：

```text
实际字段:
transport.content_type=multipart/form-data

旧验收脚本预期:
transport.type=multipart/form-data
```

分析结果本身有效。验收脚本已修复为优先读取 `content_type`，兼容旧 `type`，并额外校验：

```text
audio_field=src_audio
```

新增 `verify-only` 模式，可在不重新分析、不重新发布的情况下完成最终 T2 验收。

当前只需要执行：

```bash
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh verify-only
```

最终通过标志：

```text
LOCAL_ANALYSIS_VALID=true
REMOTE_ANALYSIS_VERIFIED=true
REMOTE_LOG_VERIFIED=true
T2_REFERENCE_ANALYSIS_ACCEPTANCE_PASS
```

## 后续顺序

```text
T2 reference analysis              WAITING VERIFY-ONLY ACCEPTANCE
T3 clip prepare                    PENDING
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
