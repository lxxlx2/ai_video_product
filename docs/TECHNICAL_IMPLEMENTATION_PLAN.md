# AI 内容生产平台技术实施方案

文档版本：V0.1  
状态：待技术评审  
上游需求：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)  
架构设计：[`TECHNICAL_DESIGN.md`](TECHNICAL_DESIGN.md)  
适用仓库：`lxxlx2/ai_video_product`  
首个落地产品：《后来没有故乡》  
首个音乐引擎：ACE-Step 1.5

## 1. 方案目标

本方案把当前已经验证过的本地 AI 音乐能力整理成一套可重复、可审核、可恢复、可被 Codex 接管的生产系统，并为视频及其他 AI 产物预留统一扩展方式。

当前阶段的核心目标：

```text
用户与 ChatGPT 确定创作要求
  ↓
Git 中形成结构化 Job
  ↓
用户执行一条命令
  ↓
系统完成预检、模型启动、提交、等待、收集、校验
  ↓
本机保存完整候选
  ↓
Git 自动发布轻量审核快照
  ↓
ChatGPT 从 Git 检查运行结果
  ↓
用户试听或观看
  ↓
继续迭代或明确批准
  ↓
最终产物进入 Git LFS
  ↓
远端验证后清理中间产物
```

后续 Codex 接管时沿用同一套 Job、脚本和状态机，仅替换人工执行入口。

## 2. 当前已知环境

### 2.1 机器

```text
Apple Silicon MacBook Pro
统一内存：48 GB
macOS：26.6.2
```

### 2.2 音乐运行时

```text
~/AI/runtime/music/acestep-1.5
```

固定上游 commit：

```text
ca1e85fe9430179831e6bc6be790c332190a3866
```

### 2.3 已安装模型

```text
acestep-v15-xl-sft
acestep-5Hz-lm-4B
acestep-v15-turbo
acestep-5Hz-lm-1.7B
Qwen3-Embedding-0.6B
vae
```

长期质量链路优先使用：

```text
DiT: acestep-v15-xl-sft
LM:  acestep-5Hz-lm-4B
Backend: MLX
```

### 2.4 当前参考音频

```text
原始文件：后来没有故乡.m4a
工作文件：后来没有故乡.reference-48k.wav
工作路径：~/AI/private/music-source/later-no-hometown/
```

原始文件和工作 WAV 各自维护独立 SHA256。

## 3. 总体系统分层

平台分为六层。

```text
L1 需求层
用户、ChatGPT、Codex

L2 控制面
Git、PRD、设计文档、Job、Prompt、Lyrics、Review、Approval

L3 编排层
Orchestrator、Preflight、State Machine、Retry、Publish

L4 Adapter 层
ACE-Step Adapter、未来其他音乐模型 Adapter、视频模型 Adapter

L5 工具层
ffmpeg、ffprobe、shasum、Git、Git LFS

L6 运行面
~/AI/runtime、~/AI/private、~/AI/logs、~/AI/run、~/AI/cache
```

依赖方向只允许从上层流向下层。具体产品脚本不能直接散落大量模型专有逻辑，模型差异逐步收敛到 Adapter。

## 4. 控制面设计

Git 作为可审计控制面，保存长期有价值且适合版本管理的内容。

保存范围：

```text
需求文档
技术设计
产品级 requirements
歌词
Style
结构化 Job
参考素材元数据及 SHA256
审核 MP3 或预览视频
请求和结果摘要
运行日志摘要
批准记录
最终产物
```

不进入 Git 的内容：

```text
模型权重
模型缓存
原始私有参考素材
完整未批准候选
大规模实验中间文件
临时转码文件
密钥、Cookie、Token
```

## 5. 本地运行面设计

统一根目录：

```text
~/AI/
```

建议结构：

```text
~/AI/runtime/           模型和运行环境
~/AI/private/           私有素材和完整候选
~/AI/logs/              长期服务日志
~/AI/run/               PID、锁、当前运行状态
~/AI/cache/             可重新生成的缓存
```

音乐实例：

```text
~/AI/runtime/music/acestep-1.5
~/AI/private/music-source/later-no-hometown
~/AI/private/music-runs/later-no-hometown/<run-id>
~/AI/logs/music/acestep-api.log
~/AI/run/music/acestep-api
```

## 6. 产品目录设计

目标目录：

```text
products/
  video/
  music/
  other/

shared/
  common/
  music/
  video/
```

当前音乐任务在兼容期继续保留原路径：

```text
music-later-no-hometown-local-reproduction/
```

等自动化至少完整通过一轮且本机工作区状态处理完成，再单独进行目录迁移。

音乐产品最终结构：

```text
products/music/<task-slug>/
  README.md
  requirements.md
  source/
  generated/
    lyrics.txt
    style.txt
  jobs/
    current.json
    reference-analysis.json
    experiments/
  review/
    latest/
  metadata/
  docs/
  output/
    final.wav
```

## 7. Job 契约

### 7.1 原则

Job 是一次生产任务的机器可执行配置。

任何会影响最终结果的关键参数必须进入 Job 或 Job 引用的版本化文件。

浏览器 UI 只用于调试，不承担生产配置保存职责。

### 7.2 顶层结构

建议 V1：

```json
{
  "schema_version": "1.0",
  "product_type": "music",
  "task_slug": "later-no-hometown",
  "ready_to_run": false,
  "mode": "experiment",
  "engine": {
    "name": "ace-step",
    "runtime": "~/AI/runtime/music/acestep-1.5",
    "dit_model": "acestep-v15-xl-sft",
    "lm_model": "acestep-5Hz-lm-4B",
    "backend": "mlx"
  },
  "inputs": {},
  "generation": {},
  "review": {},
  "publication": {}
}
```

### 7.3 ready_to_run

`ready_to_run=false` 时执行器必须拒绝开始生成。

只有在参数完成评审后才允许改为 `true`。

### 7.4 参考素材

统一结构：

```json
{
  "reference": {
    "kind": "working_wav",
    "path": "/absolute/path/reference.wav",
    "sha256": "64位十六进制"
  }
}
```

执行前校验：

```text
文件存在
SHA256 格式合法
实际 SHA256 与配置一致
ffprobe 可读取
时长和声道满足任务要求
```

### 7.5 文本输入

歌词和 Style 优先独立文件：

```text
generated/lyrics.txt
generated/style.txt
```

Job 只记录路径，便于 Git diff、人工审查和 Codex 修改。

## 8. Run 模型

每次执行创建唯一 `run_id`：

```text
YYYYMMDD-HHMMSS-xxxxxxxx
```

本地 Run：

```text
~/AI/private/music-runs/<task-slug>/<run-id>/
```

至少保存：

```text
request.json
submit_response.json
query_response.json
result.json
run.json
runner.log
server.log
candidate.wav
```

其中 `run.json` 为单次运行最终摘要。

关键字段：

```text
run_id
status
stage
error_code
error_message
started_at
ended_at
job_commit
engine
model
seed
reference_sha256
candidate_path
candidate_sha256
candidate_size
media_metadata
```

## 9. 状态机

统一 Run 状态：

```text
CREATED
PREFLIGHT
SERVICE_STARTING
SERVICE_READY
SUBMITTED
RUNNING
COLLECTING
VALIDATING
REVIEW_BUILDING
REVIEW_READY
APPROVED
PUBLISHING
PUBLISHED
CLEANUP_ELIGIBLE
FAILED
```

状态只允许按定义路径推进。

所有失败必须记录当前 stage 和稳定 error_code。

## 10. ACE-Step 服务管理

### 10.1 服务状态

```text
DOWN
HTTP_READY
MODEL_LOADING
READY
DEGRADED
FAILED
```

### 10.2 READY 判定

`/health` 返回 200 只说明 HTTP 服务可访问。

真正 READY 需要同时满足：

```text
models_initialized = true
llm_initialized = true
loaded_model = acestep-v15-xl-sft
loaded_lm_model = acestep-5Hz-lm-4B
```

### 10.3 启动策略

优先启动 REST API：

```text
127.0.0.1:8001
```

启动时：

```text
ACESTEP_CONFIG_PATH=acestep-v15-xl-sft
ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-4B
ACESTEP_LM_BACKEND=mlx
ACESTEP_NO_INIT=false
```

如果 HTTP 服务已经运行但模型未初始化，调用：

```text
POST /v1/init
```

完成 DiT 和 LM 初始化。

### 10.4 幂等要求

重复执行 `ensure_ready` 必须安全：

```text
READY 时直接返回
HTTP_READY 时补初始化
DOWN 时启动服务
FAILED 时输出明确日志并停止
```

禁止因为重复执行而再次下载已存在的完整模型。

## 11. ACE-Step Adapter

V0.1 先在当前音乐任务中验证，稳定后抽取到：

```text
shared/music/adapters/acestep.py
```

统一接口：

```text
health()
ensure_ready()
analyze_reference()
submit()
poll()
collect()
```

Adapter 负责把平台通用参数映射为 ACE-Step 字段。

常用 ACE-Step 字段：

```text
task_type
src_audio_path
reference_audio_path
full_analysis_only
thinking
vocal_language
audio_duration
inference_steps
guidance_scale
shift
audio_cover_strength
cover_noise_strength
audio_format
```

## 12. Orchestrator

长期统一入口：

```text
shared/common/run_product.py
```

第一阶段可以继续使用 shell 加 Python，但职责必须收敛。

标准执行顺序：

```text
load_job
validate_job
validate_git
validate_inputs
ensure_service_ready
submit
poll
collect
validate_media
build_review
publish_review
print_summary
```

未来对用户只暴露一条命令。

推荐形式：

```bash
make generate
```

或者：

```bash
python shared/common/run_product.py jobs/current.json
```

## 13. 参考音频分析方案

当前《后来没有故乡》先执行 `full_analysis_only`。

流程：

```text
工作 WAV
  ↓ SHA256 校验
ACE-Step audio encoder
  ↓
audio codes
  ↓
4B LM understand_audio_from_codes
  ↓
分析结果
```

保存：

```text
metadata/reference-analysis.latest.json
metadata/reference-analysis.latest.log
```

重点字段：

```text
bpm
keyscale
timesignature
duration
genre
language
caption
lyrics
audio_codes
```

模型分析只提供技术参考。用户和创作要求可以覆盖分析值。

## 14. 短片段实验方案

这是当前音乐质量问题的关键优化。

完整歌曲生成成本较高，因此引入 Experiment Gate。

### 14.1 片段选择

从参考歌曲中选择 20 到 45 秒，优先包含：

```text
主歌向副歌过渡
明显人声
主要伴奏
稳定节拍
代表性旋律
```

### 14.2 实验变量

单轮尽量只改变一到两个变量，例如：

```text
task_type
audio_cover_strength
cover_noise_strength
thinking
BPM
Key
seed
```

### 14.3 实验结果

每个实验产生独立 Run，Git review 可保留最新候选，实验矩阵写入：

```text
jobs/experiments/
metadata/experiment-summary.json
```

### 14.4 通过 Gate 的条件

需要用户主观试听确认以下方向已经可接受：

```text
旋律不明显跑调
中文人声自然
节奏稳定
风格接近目标
参考旋律保持程度符合预期
```

Gate 通过后才能提交完整 5 分钟级任务。

## 15. 完整生成方案

完整生成输出高质量 WAV 到本机 Run 目录。

生成结束执行技术校验：

```text
文件存在
文件大小超过最小阈值
ffprobe 可解析
音频时长合理
采样率合理
声道合理
SHA256 可计算
```

技术校验通过只代表文件有效，音乐质量仍由用户审核。

## 16. Review 发布方案

本地完整候选：

```text
candidate.wav
```

Git 审核版本：

```text
review/latest/review.mp3
```

建议 MP3：

```text
256 kbps
```

同步到 Git：

```text
request.json
result.json
run.json
runner.log
server.log
review.mp3
```

自动提交只允许本次 review 路径，禁止 `git add .` 和 `git add -A`。

## 17. Finalize 方案

用户批准时必须明确提供：

```text
run_id
candidate_sha256
```

Finalize：

```text
读取 Run
  ↓
确认 succeeded
  ↓
确认 candidate 存在
  ↓
重新计算 SHA256
  ↓
与用户批准 SHA256 一致
  ↓
复制到 output/final.wav
  ↓
再次校验 SHA256
  ↓
写 final-approval.json
  ↓
Git LFS commit
  ↓
push
  ↓
远端验证
```

只有远端验证完成后才进入 `CLEANUP_ELIGIBLE`。

## 18. Cleanup 方案

清理分三级。

长期保留：

```text
final
final approval
最终歌词
最终 Style
最终 Job
必要元数据
核心文档
```

审核周期保留：

```text
当前候选
最近实验
review
对应日志
```

可删除：

```text
失败候选
旧临时 WAV
旧 MP3
下载残片
空 temp
过期实验目录
可重建缓存
```

生产脚本不自动删除模型权重。

## 19. Git 和 Git LFS

媒体类型继续由 `.gitattributes` 管理。

最终大型媒体进入 Git LFS。

审核阶段优先上传压缩预览，降低 LFS 历史增长。

每次自动提交必须满足：

```text
提交范围明确
不会把其他产品脏文件带入
不会修改无关视频任务
不会覆盖用户手工改动
```

## 20. 日志和可观测性

### 20.1 日志分层

```text
服务日志：~/AI/logs/
Run 日志：~/AI/private/.../<run-id>/
Git 审核日志：review/latest/
```

### 20.2 每次 Run 必须记录

```text
时间
Git commit
Job 路径
模型
请求参数
参考 SHA
task_id
状态变化
API 错误
候选 SHA
媒体元数据
```

### 20.3 稳定错误码

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

## 21. 重试和恢复

### 21.1 可以自动重试

```text
短暂 HTTP 请求失败
query_result 暂时失败
服务 HTTP 已启动但模型尚未 READY
Git 网络 push 暂时失败
```

### 21.2 需要停止并等待人工判断

```text
参考 SHA 不一致
模型权重损坏
候选媒体无效
磁盘空间不足
Git 工作区存在高风险冲突
批准 SHA 不一致
```

### 21.3 不重复生成原则

如果模型已经成功生成 candidate，但 Git push 失败，重试必须继续发布现有 Run，禁止自动重新生成一个新候选。

## 22. 测试策略

### 22.1 单元测试

重点覆盖：

```text
Job 校验
SHA 校验
状态机
API 响应解析
结果 URL 解析
Run JSON 写入
错误码映射
```

### 22.2 集成测试

```text
API 启动
/v1/init
reference analysis
30 秒 text2music
短片段 cover
review 构建
Git path limited commit
finalize hash gate
```

### 22.3 回归测试

每次修改 shared/music 或 ACE-Step Adapter 后至少执行：

```text
API READY Gate
30 秒 smoke
一条 reference analysis
一条短片段 experiment
```

完整 5 分钟歌曲不作为日常回归测试。

## 23. 安全与数据边界

以下信息禁止进入 Git：

```text
私有令牌
API Key
Cookie
个人私密参考素材
模型平台认证信息
```

脚本输出日志时需要避免打印认证信息。

本地参考素材可以记录 SHA、格式和技术信息，但文件本体允许长期保持 LOCAL_ONLY。

## 24. Codex 接管协议

Codex 后续只需要掌握四类动作：

```text
读取 requirements 和 current job
修改歌词、Style 和 Job
执行统一入口
读取 review 和日志
```

Codex 无权自行把候选标记为最终批准。

批准仍由用户发出，系统依据 `run_id + candidate_sha256` 执行 Finalize。

## 25. 目录迁移方案

当前历史目录继续兼容。

迁移前置条件：

```text
音乐 API 自动化完整通过
至少一轮 review 自动发布成功
本地 git status 已人工确认
两个历史视频 final.mp4 删除状态得到明确处理
```

迁移采用独立提交，尽量只包含路径移动和引用更新。

目标：

```text
products/video/solana-university-video-1-something-i-shipped
products/video/solana-university-video-2-something-i-organized
products/music/later-no-hometown
```

## 26. 实施阶段

### Phase 0 文档和契约

交付：

```text
PRD
TECHNICAL_DESIGN
TECHNICAL_IMPLEMENTATION_PLAN
Job Schema 草案
状态机
错误码
```

### Phase 1 服务层稳定

完成：

```text
start
stop
status
ensure_ready
/v1/init
稳定错误输出
```

验收：重复执行安全，READY 判断准确。

### Phase 2 分析和短实验

完成：

```text
reference analysis
clip preparation
experiment job
review publication
```

验收：用户能通过 Git 试听短实验结果。

### Phase 3 完整生成

完成：

```text
full song job
完整 candidate 保存
review
run metadata
```

验收：一条命令完成整首生成到 Git review。

### Phase 4 Finalize 和 Cleanup

完成：

```text
approval gate
final.wav
Git LFS
remote verification
cleanup
```

### Phase 5 抽取 shared

把已经稳定的音乐通用逻辑抽到：

```text
shared/music
shared/common
```

### Phase 6 仓库迁移

把兼容期旧任务移入 `products/`。

### Phase 7 Codex 接管

由 Codex 自动：

```text
修改配置
执行
等待
检查
发布 review
处理可恢复错误
```

用户只负责需求和最终审核。

## 27. 当前第一批技术任务

按照优先级执行：

```text
T1 统一 ACE-Step start/status/stop/ensure_ready
T2 修复并验证 reference analysis
T3 增加 clip prepare
T4 增加 experiment job
T5 验证短片段 cover 参数
T6 验证 review 自动 push
T7 固化 full song runner
T8 验证 finalize
T9 验证 cleanup
T10 抽 shared/music
T11 目录迁移
T12 Codex 接管
```

## 28. 验收标准

V0.1 技术方案完成需要满足：

```text
用户只执行一条命令即可启动一次已批准的 Job
服务 READY 判定准确
不会无故重复下载模型
所有输入可追踪
所有候选有 Run ID
完整候选有 SHA256
失败有稳定错误码和日志
Git review 自动发布
Git 自动提交范围受控
用户批准绑定 Run ID 和 SHA256
final 可远端验证
清理不会误删 final
Codex 可以复用同一入口
```

## 29. 当前决策

当前先停止继续手工 Gradio 调参。

下一阶段先完成 Phase 1 服务层稳定，再恢复参考分析和短片段音乐实验。

这样后续所有音乐质量实验都建立在稳定执行基础上，避免把基础设施错误和模型质量问题混在一起排查。
