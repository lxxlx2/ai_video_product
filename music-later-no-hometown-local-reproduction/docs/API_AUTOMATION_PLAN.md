# ACE-Step REST 自动化方案

状态：脚本已建立，等待第一轮 API 真实运行验证。

## 目标

把日常音乐生成从 Gradio 网页迁移到可复现的本机 REST API 工作流。

当前阶段：

```text
用户和 ChatGPT 讨论歌曲
    ↓
ChatGPT 修改歌词、style、jobs/current.json
    ↓
用户执行一条命令
    ↓
脚本自动完成本地运行和 Git review 发布
    ↓
ChatGPT 从 Git 检查结果
    ↓
用户试听并反馈
```

后期：

```text
用户和 Codex 讨论歌曲
    ↓
Codex 自己写配置
    ↓
Codex 自己执行同一脚本
    ↓
Codex 检查运行结果
    ↓
用户只负责审核候选
```

## API 拓扑

```text
ChatGPT / Codex
        ↓
Git 中的结构化 job
        ↓
run_current_music_job.sh
        ↓
start_music_api_macos.sh
        ↓
ACE-Step REST API
127.0.0.1:8001
        ↓
MLX
        ↓
acestep-v15-xl-sft
acestep-5Hz-lm-4B
        ↓
本机 candidate.wav
        ↓
review.mp3 + JSON + 日志
        ↓
Git 当前分支
```

Gradio UI 继续保留作为手工诊断工具，正常工作流不依赖它。

## API 接口

ACE-Step 1.5 当前标准流程：

```text
GET  /health
POST /release_task
POST /query_result
GET  /v1/audio?path=...
```

任务提交后返回 `task_id`。查询状态：

```text
0 = queued / running
1 = succeeded
2 = failed
```

## job 配置

当前任务使用：

```text
jobs/current.json
```

它分为：

```text
任务元信息
API 地址和日志位置
本机运行目录
prompt/lyrics 文件路径
reference SHA-256
ACE-Step request 原始参数
review 发布参数
```

核心原则：尽量让 `request` 与 ACE-Step `/release_task` 原生字段一致。这样未来上游增加参数时，脚本不需要增加大量专用映射层。

典型 request：

```json
{
  "model": "acestep-v15-xl-sft",
  "lm_model_path": "acestep-5Hz-lm-4B",
  "lm_backend": "mlx",
  "task_type": "cover",
  "src_audio_path": "/absolute/path/reference.wav",
  "thinking": false,
  "vocal_language": "zh",
  "audio_duration": 335.84,
  "batch_size": 1,
  "inference_steps": 50,
  "infer_method": "ode",
  "use_random_seed": true,
  "audio_cover_strength": 1.0,
  "cover_noise_strength": 0.2,
  "audio_format": "wav",
  "dcw_enabled": false
}
```

实际参数每轮由用户和 ChatGPT/Codex 确认。

## 防误执行开关

`jobs/current.json` 必须包含：

```json
"ready_to_run": true
```

参数仍在讨论时保持 `false`。

`music_job.py` 遇到 `false` 会立即退出，避免一次误操作启动长时间完整歌曲生成。

## API 启动脚本

```text
scripts/start_music_api_macos.sh
```

职责：

1. 如果 8001 的 ACE-Step API 已健康，直接复用。
2. 如果 8215 的 Gradio 仍在运行，停止并提示用户先关闭 UI，避免同时加载两套大模型。
3. 检查 XL SFT、4B LM、Embedding、VAE 目录。
4. 固定 Apple Silicon MLX backend。
5. 固定 `ACESTEP_CONFIG_PATH=acestep-v15-xl-sft`。
6. 固定 `ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-4B`。
7. 后台启动 `acestep-api`。
8. 等待 `/health` 最长 300 秒。
9. 日志写到 `~/AI/logs/music/acestep-api.log`。

脚本不会扫描或停止其他程序。

## 单任务执行器

```text
scripts/music_job.py
```

职责：

1. 读取 job JSON。
2. 检查 `ready_to_run`。
3. 读取歌词和 style 文件。
4. 校验参考音频存在性和 SHA-256。
5. 检查 API 健康状态。
6. 调用 `/release_task`。
7. 轮询 `/query_result`。
8. 下载完整候选。
9. 计算 candidate SHA-256。
10. 通过 ffprobe 记录音频技术信息。
11. 保存本地 run 记录。
12. 将 WAV 转成 256 kbps review MP3。
13. 生成 `review/latest` 审核快照。

默认超时 7200 秒。

## 一键入口

```text
scripts/run_current_music_job.sh
```

职责：

1. 确认当前 Git 分支。
2. fetch 远端并确认本地 HEAD 与远端同步。
3. 启动或复用 ACE-Step API。
4. 调用 `music_job.py`。
5. 只 stage `review/latest`。
6. 只 commit `review/latest`。
7. push 到 `feat/local-music-reproduction-v01`。

脚本明确禁止用 `git add .` 或 `git add -A`，因此本机其他视频文件、删除状态或手动修改不会被顺带提交。

## 本机 run 结构

```text
~/AI/private/music-runs/later-no-hometown/<run-id>/
├── candidate.wav
├── request.json
├── submit_response.json
├── query_response.json
├── result.json
├── run.json
├── runner.log
└── server.log
```

完整 WAV 只留本地。

## Git review 结构

```text
review/latest/
├── review.mp3
├── request.json
├── result.json
├── run.json
├── runner.log
└── server.log
```

`review.mp3` 受仓库 `.gitattributes` 管理，会通过 Git LFS 上传。

审核文件每轮覆盖工作树中的 `latest`。历史由 commit 记录。

## 为什么不把每轮 WAV 都上传

5 分钟 WAV 通常几十 MB。每一轮都进入 LFS 会很快积累不可忽略的远端 LFS 历史。

因此：

```text
完整候选 WAV      本机保留
Git 审核试听       256 kbps MP3
最终批准 master   final.wav
```

用户批准时通过 `candidate_sha256` 绑定本机完整候选。

## 最终固化阶段

待 review 流程验证以后增加：

```text
scripts/finalize_music_candidate.sh
```

预期输入：

```text
run_id
candidate_sha256
```

它必须：

```text
读取本地 run
校验 SHA-256
复制为 output/final.wav
再次校验哈希
Git LFS commit
push
远端验证
标记 published
```

只有远端验证成功以后，任务级中间候选才进入可清理状态。

## 未来 Codex 接管

Codex 不需要操作浏览器 UI。

目标调用：

```text
Codex
  ↓ 修改 generated/lyrics.txt
  ↓ 修改 generated/style.txt
  ↓ 修改 jobs/current.json
  ↓ git push / 本地同步
  ↓ bash scripts/run_current_music_job.sh
  ↓ 读取 review/latest
  ↓ 给用户候选和判断
```

`codex-web-bridge` 只需要保证 Codex 能稳定获得模型能力和执行本地工具。音乐逻辑保持在本仓库和 ACE-Step REST API，不写进 bridge 内核。

## 当前待验证项

下一阶段只做这些：

```text
1. 停止当前 Gradio
2. pull 最新分支
3. 确认下一轮音乐参数
4. ready_to_run=true
5. 第一次执行 run_current_music_job.sh
6. 确认 API 自动启动
7. 确认结果成功落到本机 private run
8. 确认 review/latest 自动 commit/push
9. ChatGPT 从 Git 检查文件
10. 根据真实运行修脚本
```

第一次跑通后，再开始抽取 `shared/music/` 通用脚本。