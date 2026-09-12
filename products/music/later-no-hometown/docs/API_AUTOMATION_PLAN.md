# ACE-Step REST 自动化

状态：`IMPLEMENTED / 待本机真实验收`

## 目标

把 Gradio 手工配置替换成 JSON job + 固定命令，并让每轮执行自动形成 Git 审阅记录。

当前正式入口：

```text
workflows/music/ace-step/run_and_publish.sh
```

正式 runner：

```text
workflows/music/ace-step/runner.py
```

## 当前链路

```text
next-run.json
-> start_api_macos.sh
-> ACE-Step localhost REST API :8001
-> POST /release_task
-> POST /query_result
-> GET /v1/audio
-> 本地 .work 原始音频
-> ffprobe
-> preview.mp3
-> request / response / log / manifest
-> git commit
-> git push
```

## 当前人工协作模式

```text
用户 + ChatGPT 确定歌词、风格、参数
-> ChatGPT 修改 next-run.json
-> 用户 git pull
-> 用户执行一条命令
-> runner 自动完成其余步骤
-> ChatGPT 从 Git 检查日志和配置
-> 用户试听 preview.mp3
```

未来 Codex 接管后，job schema 和 runner 均保持不变，Codex 只负责自动执行命令和根据反馈修改下一轮配置。

## 为什么候选使用 MP3

默认：

```text
本地 .work: 原始 WAV
Git runs/: preview.mp3
```

这样每轮都有可听结果，同时避免大量失败 WAV 长期占用 Git LFS。

批准某个 run 后，再把对应本地 WAV 提升到：

```text
output/final.wav
```

## API 服务

启动：

```bash
bash workflows/music/ace-step/start_api_macos.sh
```

停止：

```bash
bash workflows/music/ace-step/stop_api_macos.sh
```

服务只绑定：

```text
127.0.0.1:8001
```

启动脚本默认 `--no-init`，避免先加载无关模型。具体 DiT 由 job 中的 `model` 选择。

如果检测到 Gradio 仍监听 8215，脚本会退出并要求人工停止 Gradio，不会自动 kill。

## Job 配置

项目当前入口：

```text
config/next-run.json
```

模板：

```text
workflows/music/ace-step/templates/job.example.json
```

可控制的主要字段：

```text
model
task_type
prompt / prompt_file
lyrics / lyrics_file
thinking
use_cot_caption
use_cot_language
vocal_language
bpm
key_scale
time_signature
audio_duration
inference_steps
seed
src_audio_path
reference_audio_path
audio_cover_strength
cover_noise_strength
audio_format
```

## Run 输出

每轮 Git 记录：

```text
runs/<run-id>/
  request.json
  release-response.json
  final-response.json
  run.log
  manifest.json
  ffprobe.json
  preview.mp3
```

原始结果：

```text
<repo>/.work/products/music/later-no-hometown/<run-id>/result.wav
```

## 验收 Gate

当前实现尚未在本机真实执行，因此以下项目仍待验证：

```text
G1 start_api_macos.sh 成功启动 8001
G2 /health 可用
G3 /release_task 接受 job
G4 /query_result 能正确轮询
G5 /v1/audio 能下载真实结果
G6 ffmpeg 能生成 preview.mp3
G7 runs/<run-id> 文件完整
G8 git commit + push 成功
G9 ChatGPT 能从 Git 读取该 run 文本记录
```

首轮只验证链路，不把音乐质量作为通过条件。

## 后续增强

链路通过后再加入：

1. `promote_run.py`：把用户批准的 run 提升为 final；
2. 自动技术检查：静音、削波、时长、文件有效性；
3. seed / cover strength 有界扫描；
4. run 之间的 parent_run_id 对比；
5. Codex 自动执行；
6. 最终产物远端 LFS 校验与 `.work` 清理。
