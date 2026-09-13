# AI 内容生产平台实施状态

更新时间：2026-09-13  
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

能力：

```text
status
check-ready
ensure/start
stop
restart
logs
```

READY Gate：

```text
models_initialized=true
llm_initialized=true
loaded_model=acestep-v15-xl-sft
loaded_lm_model=acestep-5Hz-lm-4B
```

幂等策略：

```text
READY        直接复用
HTTP_READY   /v1/init
DEGRADED     /v1/init 修正模型状态
DOWN         启动 REST API
FAILED       拒绝操作未知进程
```

安全边界：

```text
不删除模型
不抢占未知 8001 监听程序
Gradio 8215 仍运行时拒绝新启 REST API
stop 只终止可识别 ACE-Step 进程
```

### T1 本地验收结果

2026-09-13 本地验收通过。

验证路径：

```text
READY 初始状态
  ↓
stop
  ↓
DOWN
  ↓
ensure from DOWN
  ↓
READY_REUSED=false
  ↓
ensure while READY
  ↓
READY_REUSED=true
  ↓
最终 READY
```

通过标志：

```text
T1_SERVICE_ACCEPTANCE_PASS
```

最终模型状态：

```text
MODELS_INITIALIZED=true
LLM_INITIALIZED=true
LOADED_MODEL=acestep-v15-xl-sft
LOADED_LM_MODEL=acestep-5Hz-lm-4B
```

## Phase 2 / T2 参考音频深度分析

状态：`RETRY AFTER MULTIPART FIX`

当前实现：

```text
music-later-no-hometown-local-reproduction/scripts/reference_analysis.py
music-later-no-hometown-local-reproduction/scripts/run_reference_analysis.sh
music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh
music-later-no-hometown-local-reproduction/jobs/reference-analysis.json
music-later-no-hometown-local-reproduction/docs/REFERENCE_ANALYSIS_OPERATIONS.md
```

T2 目标：

```text
验证工作 WAV SHA256
验证 ffprobe
复用 T1 ensure_ready
通过 multipart src_audio 上传参考 WAV
执行 full_analysis_only
保存 task_id / request / transport / health / engine commit / Git commit
提取 BPM / Key / Time Signature / Duration / Genre / Language / Caption
保留 audio_codes 和 metas
自动提交并 push 分析快照
验证远端与本地一致
```

### 第一次本地验收结果

2026-09-13 第一次验收完成了 READY、SHA256、ffprobe 和版本记录 Gate，在任务提交阶段失败：

```text
ERROR_CODE=API_SUBMIT_FAILED
HTTP 400 Bad Request
{"detail":"absolute audio file paths are not allowed"}
```

固定的 ACE-Step commit 对 `/release_task` 的绝对音频路径执行安全限制。JSON 中传入 `/Users/...reference-48k.wav` 会被拒绝；multipart 上传字段 `src_audio` 会由 ACE-Step 保存到允许的系统临时目录。

已完成修复：

```text
reference_analysis.py
  本机路径继续用于 SHA256 / ffprobe / 运行记录
  API 提交改用 multipart/form-data
  工作 WAV 上传字段 src_audio
  JSON/结果新增 transport 记录

music_job.py
  src_audio_path       -> multipart src_audio
  reference_audio_path -> multipart reference_audio
  无本地音频输入       -> application/json
```

该修复同时覆盖后续短片段 cover/remix 和完整歌曲任务，避免 T5/T7 再遇到相同错误。

输出：

```text
music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.json
music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.log
```

Git 发布失败时允许：

```bash
bash music-later-no-hometown-local-reproduction/scripts/run_reference_analysis.sh publish-only
```

该模式只重试已有分析结果的发布，不重新执行模型分析。

### T2 本地重验

执行：

```bash
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh
```

提交阶段应出现：

```text
transport=multipart/form-data
audio_field=src_audio
task_id=...
```

最终通过标志：

```text
T2_REFERENCE_ANALYSIS_ACCEPTANCE_PASS
```

T2 PASS 后进入：

```text
T3 clip prepare
T4 experiment job
T5 short cover experiment
```

## 后续顺序

```text
T2 reference analysis              RETRY AFTER MULTIPART FIX
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
