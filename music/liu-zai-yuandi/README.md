# 留在原地的家 | ACE-Step 1.5 本地原创音乐 V1

这是未批准发布的音乐草稿，存于独立 music/ 目录。这里只有原创歌词、参数和本地生成脚本；没有正式音频，不改变视频 output/final.mp4 的审批规则。

## 运行状态

- 已核对 ACE-Step 官方 POST /release_task、POST /query_result、GET /v1/audio、GET /health 文档。
- Python 3.9+ 标准库客户端，仅调用 127.0.0.1/localhost，不启动服务器、不自动下载模型或安装包。
- output/ 已加入 .gitignore，生成音频不自动发布 Git。
- 真实 Mac 推理、当前模型是否仍完整及音质有待本机验证。

## 终端 A：启动原有 ACE-Step

根据你的终端截图，旧脚本存在于：

    /Users/jerson/AI/runtime/music/acestep-1.5/start_api_server_macos.sh

使用：

    cd "$HOME/AI/runtime/music/acestep-1.5"
    ls -l start_api_server_macos.sh
    ./start_api_server_macos.sh

注意：官方启动脚本可能自动检查更新、安装缺失依赖，模型缺失时也可能下载。请先确认已有运行环境可复用，避免在不知情的情况下改变本机环境。启动后保留此终端。

## 终端 B：首次拉取任务分支并生成

若尚未克隆：

    cd "$HOME"
    git clone https://github.com/lxxlx2/ai_video_product.git
    cd "$HOME/ai_video_product"
    git fetch origin feat/music-liu-zai-yuandi-20261106
    git switch --track origin/feat/music-liu-zai-yuandi-20261106

已有克隆先确保无未提交修改，再在克隆目录内 fetch/switch。切勿盲目覆盖已有工作目录。

进入歌曲目录并运行：

    cd music/liu-zai-yuandi
    curl -fsS http://127.0.0.1:8001/health
    python3 generate.py --dry-run
    python3 generate.py
    open output/liu_zai_yuandi_v1.mp3

你之前在 ~ 执行 generate.py，导致程序寻找 /Users/jerson/generate.py。请始终在本目录运行。

## 参数

- lyrics.txt：原创中文歌词，包含与霄宝、元宝及在外生活有关的内容。
- config.json：中文男声，伤感抒情流行和旋律说唱，80 BPM，D Minor，210秒。
- acestep-v15-turbo，8步，batch_size=1，固定 seed。
- 成功后输出 MP3、请求/结果 JSON 和 SHA256。已生成音频不会覆盖；第二版执行 python3 generate.py --out ./output-v2。
- 如端口不同，执行 python3 generate.py --api http://127.0.0.1:实际端口。

## 诊断

- Connection refused：后台服务没启动或实际端口不同，先查看 /health。
- No such file or directory：检查 pwd 并进入正确的目录。
- Model not found：查看 /v1/models 和已有模型缓存，不要直接重新下载。
- TIMEOUT：任务可能仍在运行，查看 output/submit.json 和 API 日志，避免重复提交。
- 内存不足：停止本次 ACE-Step 生成，保持本机其他正常工作与生产任务不受影响。

接口文档：https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md
