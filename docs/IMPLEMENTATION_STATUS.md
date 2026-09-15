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

实现：

```text
music-later-no-hometown-local-reproduction/scripts/music_api_service.sh
music-later-no-hometown-local-reproduction/scripts/start_music_api_macos.sh
music-later-no-hometown-local-reproduction/scripts/status_music_api_macos.sh
music-later-no-hometown-local-reproduction/scripts/stop_music_api_macos.sh
music-later-no-hometown-local-reproduction/scripts/ensure_music_api_ready.sh
music-later-no-hometown-local-reproduction/scripts/accept_music_api_service.sh
music-later-no-hometown-local-reproduction/docs/SERVICE_OPERATIONS.md
```

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

状态：`ANALYSIS PASS, WAITING PUBLISH-ONLY ACCEPTANCE`

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

固定 ACE-Step commit 会拒绝系统临时目录之外的绝对音频路径。已将参考音频和后续本地音频输入统一改成 multipart 文件上传。

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

这些字段属于模型分析结果，后续短片段实验继续以实际试听作为质量 Gate。

### T2 发布阶段修复

模型分析结束后，Git 发布受到任务级 `.gitignore` 的 `*.log` 规则影响：

```text
metadata/reference-analysis.latest.log
```

已修复：

```text
.gitignore
  允许 metadata/reference-analysis.latest.log
  允许 review/latest/runner.log
  允许 review/latest/server.log

run_reference_analysis.sh
  精确发布 allowlist
  对固定 JSON/log 使用 git add -f

accept_reference_analysis.sh
  支持 publish-only
  不重新执行模型分析
  验证远端 JSON 和 log 均存在且与本地一致
```

当前只需要执行：

```bash
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh publish-only
```

最终通过标志：

```text
REFERENCE_ANALYSIS_PUBLISHED
LOCAL_ANALYSIS_VALID=true
REMOTE_ANALYSIS_VERIFIED=true
REMOTE_LOG_VERIFIED=true
T2_REFERENCE_ANALYSIS_ACCEPTANCE_PASS
```

## 后续顺序

```text
T2 reference analysis              WAITING PUBLISH-ONLY ACCEPTANCE
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
