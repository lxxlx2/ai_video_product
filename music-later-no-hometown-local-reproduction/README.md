# 《后来没有故乡》本地音乐任务

这个目录记录《后来没有故乡》的本地生成、参考复现、自动化审核和最终固化流程。

当前目标已经调整：先把 ACE-Step 作为可脚本化的本地音乐引擎跑通，再逐步提高音乐质量。网页 UI 只保留调试用途，正常工作流转向 REST API 和命令脚本。

## 当前状态

截至 2026-09-12：

```text
Apple Silicon 预检                    PASS
ACE-Step 1.5 安装                     PASS
参考音频校验与 48 kHz WAV 转换        PASS
acestep-v15-xl-sft                    PASS
acestep-5Hz-lm-4B                     PASS
MLX DiT                               PASS
MLX LM                                PASS
30 秒本地生成                         PASS
完整 5:36 Remix/Cover                 可以执行，但音乐质量未达要求
旧下载残片清理                        PASS
REST API 自动化脚本                   已建立，待首次真实运行验证
Codex 全自动编排                      等 codex-web-bridge 稳定后接管
```

## 当前参考文件

原始参考：

```text
后来没有故乡.m4a
SHA-256: 176c81b30cbd68de6cd7c900d1513160f9a6a591eb7e9bed65d848f273c48b0e
时长: 335.840 秒
采样率: 48000 Hz
```

本机工作参考：

```text
/Users/jerson/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav
```

参考音频本体不上传本仓库。

## 当前运行方式

新的运行契约是：

```text
ChatGPT / Codex 与用户确认歌词和生成方向
    ↓
更新 jobs/current.json
    ↓
ready_to_run=true
    ↓
用户当前阶段执行 run_current_music_job.sh
    ↓
脚本启动/复用本机 ACE-Step REST API
    ↓
自动提交任务并等待结果
    ↓
完整候选保存在 ~/AI/private/music-runs/
    ↓
自动生成 review/latest/review.mp3
    ↓
同步请求、结果、SHA-256、runner 日志、server 日志
    ↓
自动 commit + push 当前 review
    ↓
ChatGPT / Codex 从 Git 检查
    ↓
用户试听并决定继续迭代或批准
```

当前 `jobs/current.json` 默认 `ready_to_run=false`。每轮参数需要先确认，避免误触后直接生成一首耗时较长的完整歌曲。

## 下一轮执行命令

参数确认并写入 Git 后，本机先同步：

```bash
cd /Users/jerson/ai_video_product
git switch feat/local-music-reproduction-v01
git pull --ff-only origin feat/local-music-reproduction-v01
```

如果 8215 的 Gradio UI 仍在运行，在它自己的终端按 `Ctrl+C` 结束。

然后：

```bash
cd /Users/jerson/ai_video_product/music-later-no-hometown-local-reproduction
bash scripts/run_current_music_job.sh
```

脚本会拒绝以下危险状态：

```text
当前分支错误
本地分支落后远端
8215 Gradio 仍占用并加载模型
8001 被未知服务占用
关键模型目录缺失
job 未标记 ready_to_run
参考文件 SHA-256 不一致
```

## API 服务

API 启动脚本：

```text
scripts/start_music_api_macos.sh
```

默认：

```text
host: 127.0.0.1
port: 8001
backend: MLX
DiT: acestep-v15-xl-sft
LM: acestep-5Hz-lm-4B
```

服务日志：

```text
~/AI/logs/music/acestep-api.log
```

API 服务可以常驻。后续 Codex 直接调用同一服务。

## 单次运行产物

本机完整结果：

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

Git 审核快照：

```text
review/latest/
├── review.mp3
├── request.json
├── result.json
├── run.json
├── runner.log
└── server.log
```

Git 上传的是审核 MP3。完整 WAV 留本机。这样可以让 ChatGPT/Codex 从 Git 检查每次运行，同时控制 Git LFS 历史体积。

## 最终产物

用户批准某个候选以后，批准必须绑定到 `run.json` 中的：

```text
candidate_sha256
```

随后才把准确候选固化为：

```text
output/final.wav
```

最终 WAV 使用 Git LFS。

## 当前模型资产

已安装：

```text
acestep-v15-xl-sft       ~19G
acestep-5Hz-lm-4B        ~7.9G
acestep-v15-turbo        ~4.5G
acestep-5Hz-lm-1.7B      ~3.5G
Qwen3-Embedding-0.6B     ~1.1G
vae                       ~337M
```

当前先全部保留。Turbo 和 1.7B 后续只有在 API 和启动逻辑验证不会自动重新下载时再考虑删除。

## 目录说明

```text
config/       固定运行配置和模型信息
generated/    歌词和 style
jobs/         当前结构化生成任务
review/       最近一次 Git 审核快照
metadata/     参考哈希、安装、预检等证据
docs/         流程、规划、自动化和清理说明
scripts/      安装、API、运行和后续固化脚本
output/       只有明确批准的最终音频
source/       公开的 source 说明，不保存私有参考音频
```

## 关键文档

```text
docs/PROGRESS_2026-09-12.md
docs/API_AUTOMATION_PLAN.md
docs/CODEX_ORCHESTRATION.md
docs/REPRODUCTION_RUNBOOK.md
docs/RETENTION_AND_CLEANUP.md
```

## 当前最重要的结论

ACE-Step 本地推理能力已经跑通。当前主要问题在音乐质量和生成控制，并非安装或 MLX 执行失败。

后续每次实验都必须进入结构化 job 和 Git review 流程，避免继续通过网页手工改大量参数。这样无论当前由 ChatGPT 指导，还是后续由 Codex 全自动执行，都使用同一套可追踪流程。