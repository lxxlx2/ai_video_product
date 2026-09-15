# AI 内容生产平台技术设计

文档版本：V0.1  
状态：Draft，进入技术评审  
上游需求：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)  
适用仓库：`lxxlx2/ai_video_product`

## 1. 设计目标

本设计把 `ai_video_product` 建设为一个以 Git 为控制面、以本机 `~/AI/` 为运行面、以结构化 Job 为执行契约的 AI 内容生产平台。

核心目标：

```text
需求可表达
配置可审查
执行可自动化
结果可追踪
候选可审核
最终文件可验证
失败可恢复
临时文件可清理
模型可替换
Codex 可接管
```

首个落地链路是 Apple Silicon 上的 ACE-Step 1.5 音乐生成，后续同一架构扩展到视频、图片和其他 AI 产物。

## 2. 设计原则

### 2.1 控制面与运行面分离

Git 仓库保存：

```text
需求
设计
Job
提示词
歌词或脚本
元数据
审核快照
批准记录
最终产物
```

本机 `~/AI/` 保存：

```text
模型运行时
模型权重
私有参考素材
完整候选
临时文件
服务状态
大体积日志
缓存
```

### 2.2 Job 是唯一执行真相

生产任务不得依赖浏览器 UI 当前状态。

一次生成的所有关键输入必须能由结构化 Job 完整描述。

### 2.3 Agent 与执行器解耦

ChatGPT、Codex、人工终端都只负责修改或执行相同的 Job 和脚本。

后续更换 Agent 时无需重写底层生产流程。

### 2.4 模型通过 Adapter 接入

上层工作流使用统一概念：

```text
generate
analyze
cover
remix
repaint
finalize
```

具体模型差异收敛到 Adapter 或模型专用配置层。

### 2.5 先短验证，再长生成

任何高成本任务先通过小规模 Gate。

音乐典型顺序：

```text
模型加载
  ↓
30 秒 smoke test
  ↓
参考分析
  ↓
短片段参数验证
  ↓
完整歌曲
```

## 3. 总体架构

```text
┌──────────────────────────────┐
│ 用户 / ChatGPT / Codex       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Git 控制面                   │
│ PRD / Design / Job / Review  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Orchestrator                 │
│ preflight / submit / poll    │
│ collect / validate / publish │
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌──────────────┐  ┌──────────────┐
│ Model Adapter│  │ Media Tools  │
│ ACE-Step 等  │  │ ffmpeg 等    │
└──────┬───────┘  └──────┬───────┘
       │                 │
       └────────┬────────┘
                ▼
┌──────────────────────────────┐
│ ~/AI 本地运行面             │
│ runtime/private/logs/run     │
└──────────────────────────────┘
```

## 4. 仓库目标结构

```text
ai_video_product/
├── README.md
├── .gitattributes
├── docs/
│   ├── README.md
│   ├── PRODUCT_REQUIREMENTS.md
│   ├── TECHNICAL_DESIGN.md
│   ├── REPOSITORY_STRUCTURE.md
│   └── PRODUCT_WORKFLOW.md
├── products/
│   ├── video/
│   │   └── <task-slug>/
│   ├── music/
│   │   └── <task-slug>/
│   └── other/
│       └── <task-slug>/
├── shared/
│   ├── common/
│   ├── music/
│   └── video/
└── <兼容期旧任务目录>/
```

当前旧任务目录暂时保留，迁移规则见第 18 节。

## 5. 产品任务标准结构

### 5.1 音乐任务

```text
products/music/<task-slug>/
├── README.md
├── requirements.md
├── source/
│   └── README.md
├── generated/
│   ├── lyrics.txt
│   └── style.txt
├── jobs/
│   ├── current.json
│   ├── reference-analysis.json
│   └── history/
├── review/
│   └── latest/
│       ├── review.mp3
│       ├── request.json
│       ├── result.json
│       ├── run.json
│       ├── runner.log
│       └── server.log
├── metadata/
│   ├── reference.json
│   └── final-approval.json
├── docs/
│   ├── progress.md
│   └── decisions.md
└── output/
    └── final.wav
```

### 5.2 视频任务

```text
products/video/<task-slug>/
├── README.md
├── requirements.md
├── source/
├── generated/
├── jobs/
├── review/
├── metadata/
├── docs/
└── output/
    └── final.mp4
```

## 6. 本机目录规范

```text
~/AI/
├── runtime/
│   ├── music/
│   └── video/
├── private/
│   ├── music-source/
│   ├── music-runs/
│   ├── video-source/
│   └── video-runs/
├── logs/
│   ├── music/
│   └── video/
├── run/
│   ├── music/
│   └── video/
└── cache/
```

当前 ACE-Step 固定运行时：

```text
~/AI/runtime/music/acestep-1.5
```

当前《后来没有故乡》参考素材：

```text
~/AI/private/music-source/later-no-hometown/
```

候选运行目录：

```text
~/AI/private/music-runs/later-no-hometown/<run-id>/
```

## 7. Job Schema

V0.1 使用 JSON，后续可增加 JSON Schema 文件进行严格校验。

推荐顶层结构：

```json
{
  "job_version": 1,
  "product_type": "music",
  "task_slug": "later-no-hometown",
  "ready_to_run": false,
  "engine": {
    "name": "ace-step",
    "runtime": "~/AI/runtime/music/acestep-1.5"
  },
  "inputs": {},
  "request": {},
  "review": {},
  "publication": {}
}
```

### 7.1 通用字段

必须包含：

```text
job_version
product_type
task_slug
ready_to_run
engine
```

### 7.2 参考资产

建议统一：

```json
{
  "reference": {
    "kind": "working_wav",
    "path": "/absolute/path/reference.wav",
    "sha256": "..."
  }
}
```

任何使用参考文件的任务，执行前必须验证 SHA-256。

### 7.3 内容输入

较长内容不直接塞入 Job，优先引用仓库文件：

```json
{
  "prompt_file": "../generated/style.txt",
  "lyrics_file": "../generated/lyrics.txt"
}
```

这样方便 Git diff 和人工审核。

## 8. Run 数据模型

每次执行生成唯一 Run ID：

```text
YYYYMMDD-HHMMSS-<8-char-random>
```

单次本地 Run 目录：

```text
<run-id>/
├── request.json
├── submit_response.json
├── query_response.json
├── result.json
├── run.json
├── runner.log
├── server.log
└── candidate.<ext>
```

`run.json` 是该 Run 的最终摘要，至少包含：

```text
run_id
status
error
started_at
ended_at
task_id
job_file
engine
model
candidate_local_path
candidate_sha256
candidate_size
ffprobe / media metadata
request
API 查询结果摘要
```

## 9. Run 状态机

平台统一状态：

```text
CREATED
  ↓
PREFLIGHT
  ↓
SERVICE_READY
  ↓
SUBMITTED
  ↓
RUNNING
  ↓
COLLECTING
  ↓
VALIDATING
  ↓
REVIEW_READY
```

失败可发生于任意阶段并进入：

```text
FAILED
```

用户批准后：

```text
REVIEW_READY
  ↓
APPROVED
  ↓
PUBLISHED
  ↓
CLEANUP_ELIGIBLE
```

`FAILED` 和 `REVIEW_READY` 都允许产生 Git review 快照。

## 10. 错误码

脚本对外输出稳定错误码：

```text
PRECHECK_FAILED
WRONG_BRANCH
REMOTE_OUT_OF_SYNC
SOURCE_MISSING
REFERENCE_INVALID
SERVICE_START_FAILED
MODEL_INIT_FAILED
MODEL_NOT_READY
API_SUBMIT_FAILED
API_POLL_FAILED
GENERATION_FAILED
RESULT_INVALID
MEDIA_VALIDATE_FAILED
REVIEW_BUILD_FAILED
GIT_COMMIT_FAILED
GIT_PUSH_FAILED
FINAL_HASH_MISMATCH
FINAL_PUBLISH_FAILED
CLEANUP_BLOCKED
```

错误日志需要附带人类可读解释。

## 11. 模型服务生命周期

### 11.1 服务状态

统一定义：

```text
DOWN
HTTP_READY
MODEL_LOADING
READY
DEGRADED
FAILED
```

### 11.2 READY 条件

以 ACE-Step 为例，READY 必须同时满足：

```text
/health 可访问
models_initialized = true
llm_initialized = true
loaded_model = 期望 DiT
loaded_lm_model = 期望 LM
```

仅 `/health` 返回 200 不满足 READY。

### 11.3 启动策略

V0.1 优先 eager load：

```text
ACESTEP_NO_INIT=false
```

如果发现已有 HTTP 服务但模型未加载，则通过：

```text
POST /v1/init
```

完成按需初始化。

### 11.4 模型文件管理

服务启动前只检查必要模型目录存在，不主动删除或重下载模型。

模型权重清理由单独维护流程执行，生产脚本不得隐式删除模型。

## 12. Model Adapter

建议后续从产品任务目录抽象：

```text
shared/music/adapters/
├── base.py
└── acestep.py
```

统一接口概念：

```text
health()
ensure_ready()
analyze_reference()
submit(job)
poll(task_id)
collect(result)
```

ACE-Step Adapter 负责字段转换，例如：

```text
task_type
src_audio_path
reference_audio_path
full_analysis_only
thinking
audio_duration
inference_steps
audio_cover_strength
cover_noise_strength
```

上层 Orchestrator 不直接依赖这些字段含义。

## 13. Orchestrator

长期目标为一个统一入口：

```text
shared/common/run_product.py
```

或通过 Makefile：

```bash
make analyze
make generate
make finalize RUN_ID=... SHA256=...
make cleanup
```

V0.1 可以继续由各产品脚本实现，但接口需要逐步收敛。

Orchestrator 职责：

```text
读取 Job
校验 Job
校验 Git 分支
校验远端同步
校验参考文件
确保模型 READY
提交任务
轮询
收集产物
媒体技术检查
生成 review
限定路径 commit
push
输出 Run ID 和 SHA
```

## 14. 音乐生产技术流程

### 14.1 参考分析

```text
reference.wav
  ↓ SHA 校验
ACE-Step full_analysis_only
  ↓
BPM / Key / Time Signature / Genre / Language / Caption / Audio Codes
  ↓
metadata/reference-analysis.latest.json
```

分析结果不直接覆盖人工创作要求，后续生成 Job 可以明确选择自动值或人工修正值。

### 14.2 短片段参数验证

完整 5 分钟生成前，从参考歌曲选择 20 到 45 秒代表片段。

验证：

```text
旋律保持程度
调性感
人声自然度
中文咬字
配器方向
cover/remix 参数
```

短片段通过后才允许完整运行。

### 14.3 完整生成

完整任务输出 WAV，保留在本地 Run 目录。

技术检查至少执行：

```text
文件存在
文件大小 > 最小阈值
ffprobe 可解析
时长合理
采样率合理
声道合理
SHA-256 计算成功
```

### 14.4 Review

完整 WAV 转成审核 MP3：

```text
256 kbps MP3
```

Git `review/latest/` 保存：

```text
review.mp3
request.json
result.json
run.json
runner.log
server.log
```

每次新 Run 覆盖工作树中的 `latest`，历史由 Git commit 保存。

## 15. 人工审核与 Finalize

用户明确批准时提供：

```text
run_id
candidate_sha256
```

Finalize 流程：

```text
读取 run.json
  ↓
确认 status=succeeded
  ↓
检查本地 candidate 存在
  ↓
重新计算 SHA-256
  ↓
与批准 SHA 比对
  ↓
复制为 output/final.*
  ↓
再次计算 SHA
  ↓
写 final-approval.json
  ↓
Git LFS commit
  ↓
push
  ↓
远端验证
```

任何 SHA 不一致立即停止。

## 16. Git 提交策略

### 16.1 自动脚本禁止

```text
git add .
git add -A
```

### 16.2 自动脚本只允许提交任务自己拥有的路径

例如音乐 review：

```text
<task>/review/latest/
```

最终发布：

```text
<task>/output/final.wav
<task>/metadata/final-approval.json
```

### 16.3 本地其他脏文件

其他产品的脏状态不得阻塞当前任务的精确路径提交，也不得被自动提交。

如果当前任务自身的受控路径存在无法解释的人工修改，则停止并要求处理。

## 17. Git LFS 策略

最终大型媒体进入 LFS。

审核预览可以根据体积决定普通 Git 或 LFS，V0.1 继续遵循现有 `.gitattributes`。

禁止把每轮完整 WAV 都上传 LFS，因为 LFS 历史对象会持续消耗空间。

推荐：

```text
候选完整 WAV      本地
候选 review.mp3   Git
最终 final.wav    Git LFS
```

## 18. 仓库迁移设计

当前顶层旧目录：

```text
solana-university-video-1-something-i-shipped/
solana-university-video-2-something-i-organized/
music-later-no-hometown-local-reproduction/
```

目标：

```text
products/video/solana-university-video-1-something-i-shipped/
products/video/solana-university-video-2-something-i-organized/
products/music/later-no-hometown/
```

迁移前置条件：

```text
当前生成任务停止
音乐自动化至少成功完成一轮 review
本机 git status 已人工确认
两个历史 final.mp4 删除状态得到明确处理
```

迁移使用独立 commit，尽量只包含 rename/move。

迁移完成后再单独更新脚本相对路径并做回归测试，避免“目录移动”和“逻辑修改”混在一个提交中。

## 19. 清理设计

### 19.1 清理前置 Gate

满足以下条件才能清理已批准候选：

```text
final 已生成
final SHA 与批准 SHA 一致
Git commit 成功
Git push 成功
远端 LFS/文件可验证
```

### 19.2 可自动清理

```text
失败 Run 的大型 candidate
转码临时文件
过期 preview
模型下载残片
明确标记的 cache
```

### 19.3 不自动清理

```text
模型正式权重
私有参考原件
当前审核候选
未完成远端验证的批准候选
```

## 20. 安全与隐私

严禁提交：

```text
API key
cookie
token
.env
钱包密钥
个人隐私参考素材
```

脚本日志需要避免完整打印凭据。

私有参考文件使用 SHA 和 metadata 建立可追踪关系，内容本身保持本地。

## 21. Codex 接管协议

Codex 后续只需要遵循稳定入口：

```text
读取 PRD / 产品 requirements
读取当前 Job
修改 generated 内容和 Job
执行 analyze/generate/finalize/cleanup 命令
读取退出码和日志
检查 Git review
等待用户审核
```

Codex 不需要直接控制 Gradio UI。

Codex 不得跳过：

```text
SHA 校验
READY 校验
短任务 Gate
人工最终批准
远端验证后清理 Gate
```

## 22. V0.1 技术里程碑

### T0 文档基线

```text
PRD
技术设计
仓库结构
产品工作流
```

### T1 ACE-Step 服务稳定化

```text
启动
模型 READY 检查
/v1/init 恢复
日志
停止/重启策略
```

### T2 参考分析

```text
reference SHA
full_analysis_only
结果落盘
Git 发布
```

### T3 短片段实验

```text
自动裁切
结构化参数
20 到 45 秒候选
review 发布
```

### T4 完整音乐 Run

```text
一条命令
完整 WAV
review MP3
日志
Git push
```

### T5 Finalize

```text
run_id + SHA 批准
final.wav
Git LFS
远端验证
```

### T6 Cleanup

```text
安全删除实验产物
保留最终产物和必要记录
```

### T7 共享能力抽取

将验证稳定的音乐脚本从具体歌曲目录抽到 `shared/music/`。

### T8 Codex 接管

`codex-web-bridge` 稳定后，Codex 使用相同命令完成 T1 到 T6。

## 23. 当前已知技术债

1. 当前音乐脚本仍位于具体歌曲目录，尚未抽到 `shared/music/`。
2. Job 尚无正式 JSON Schema。
3. 服务 stop/restart/status 入口尚未统一。
4. review 发布和生成逻辑仍有部分脚本耦合。
5. 参考分析流程尚未完成首次成功验证。
6. 当前完整 Cover/Remix 质量未达要求，需要先做短片段实验体系。
7. 两个历史视频目录存在本地 `final.mp4` 删除状态，仓库迁移暂缓。

## 24. 下一步实现顺序

技术评审通过后严格按以下顺序推进：

```text
1. 修正并验证 ACE-Step API READY
2. 完成参考音频深度分析
3. 建立短片段实验脚本和 Job
4. 用短片段找到可接受参数
5. 运行完整歌曲
6. 验证 review 自动发布
7. 验证 final 批准流程
8. 验证 cleanup
9. 抽取 shared/music
10. 迁移 products/ 目录
11. 接入 Codex
```

在第 4 步通过前，不继续盲目执行完整 5 分钟歌曲生成。