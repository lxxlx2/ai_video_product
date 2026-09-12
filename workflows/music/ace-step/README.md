# ACE-Step 命令化音乐工作流

这套目录是音乐项目共用的执行层。目标是把 Gradio 页面上的手工点击改造成稳定的命令和 JSON job。

## 当前执行模型

```text
ChatGPT 更新产品目录中的 next-run.json
        ↓
用户 git pull
        ↓
bash workflows/music/ace-step/run_and_publish.sh <job.json>
        ↓
如果 8001 API 未启动，脚本启动本地 ACE-Step REST API
        ↓
提交 /release_task
        ↓
轮询 /query_result
        ↓
下载原始结果到 .work
        ↓
生成 Git 审阅 preview.mp3
        ↓
保存 request / response / log / manifest / ffprobe
        ↓
git commit + push
        ↓
ChatGPT 检查 Git，用户试听 preview
```

后续 Codex 直接执行同一条命令即可。

## 前置条件

本机已经安装 ACE-Step：

```text
~/AI/runtime/music/acestep-1.5
```

并且已经下载所需模型。

依赖：

```text
git
python3
curl
ffmpeg
ffprobe
uv
```

## 一次性从 Gradio 切到 API

如果当前 `127.0.0.1:8215` 的 Gradio 还在运行，先在启动它的终端按 `Ctrl+C`。

脚本不会自动杀掉 Gradio，也不会扫描式 kill 其他进程。

之后执行：

```bash
bash workflows/music/ace-step/start_api_macos.sh
```

API 地址：

```text
http://127.0.0.1:8001
```

API 使用 MLX，默认 `--no-init` 启动，真正需要的 DiT 会在 job 请求时加载，避免先加载无关默认模型。

## 每次运行

推荐直接用一条命令：

```bash
bash workflows/music/ace-step/run_and_publish.sh \
  products/music/later-no-hometown/config/next-run.json
```

如果 API 已经在运行，脚本直接复用。若 API 未运行且 8215 未占用，脚本会启动 API。

## Job 文件

示例见：

```text
workflows/music/ace-step/templates/job.example.json
```

项目中的正式下一轮配置建议固定叫：

```text
products/<type>/<project>/config/next-run.json
```

ChatGPT 每次调参直接修改这个文件。

## 生成结果

原始高质量结果留在本机：

```text
.work/products/music/<project>/<run-id>/result.wav
```

Git 审阅目录：

```text
products/music/<project>/runs/<run-id>/
```

默认提交：

```text
request.json
release-response.json
final-response.json
run.log
manifest.json
ffprobe.json
preview.mp3
```

`preview.mp3` 用于快速试听和减少 Git LFS 增长。批准后再把对应的本地 WAV 提升为 `output/final.wav`。

## 失败也会留记录

API 提交失败、推理失败、下载失败等情况，runner 仍尽可能生成失败 manifest 和 run.log，并提交到 Git，方便 ChatGPT 直接定位问题。

## 停止 API

```bash
bash workflows/music/ace-step/stop_api_macos.sh
```

停止脚本只会停止由 `start_api_macos.sh` 记录的 PID，并校验该 PID 的命令行，避免误杀其他程序。

## 重要参数

ACE-Step API 已支持：

```text
model
prompt
lyrics
thinking
vocal_language
bpm
key_scale
time_signature
audio_duration
inference_steps
seed
src_audio_path
reference_audio_path
task_type
audio_cover_strength
cover_noise_strength
audio_format
```

因此 Gradio 只保留作调试和探索用途，正式生成不依赖页面点击。

## 当前安全策略

- 服务只绑定 `127.0.0.1`。
- 不自动上传参考音频。
- `.work/` 被 Git 忽略。
- 不自动 kill 8215 Gradio。
- 不修改 ACE-Step 上游源码。
- 不关闭浏览器、Codex、IDE 等无关程序。
