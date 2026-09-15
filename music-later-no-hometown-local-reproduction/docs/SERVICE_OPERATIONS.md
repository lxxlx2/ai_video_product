# ACE-Step 服务运维说明

文档版本：V0.1  
适用阶段：T1 服务层稳定  
平台：macOS Apple Silicon  
服务：ACE-Step 1.5 REST API

## 1. 目标

将 ACE-Step 从“手工启动一次即可”的实验状态整理成可被脚本、ChatGPT 和后续 Codex 稳定调用的本地服务。

统一服务入口：

```text
scripts/music_api_service.sh
```

支持：

```text
status
check-ready
ensure
start
stop
restart
logs
```

其中生产流程统一调用 `ensure`。

## 2. READY 定义

HTTP 端口可访问只代表服务进程已经响应。

真正 READY 必须同时满足：

```text
models_initialized=true
llm_initialized=true
loaded_model=acestep-v15-xl-sft
loaded_lm_model=acestep-5Hz-lm-4B
```

因此服务状态分为：

```text
DOWN
HTTP_READY
DEGRADED
READY
FAILED
```

含义：

```text
DOWN         8001 没有监听，/health 不可访问
HTTP_READY   ACE-Step HTTP 已响应，但 DiT/LM 尚未加载
DEGRADED     只加载部分模型，或加载的模型和期望配置不一致
READY        HTTP、DiT、LM 和模型名称全部符合生产要求
FAILED       端口被占用、health 无法识别或状态不一致
```

## 3. 统一配置

默认：

```text
runtime: ~/AI/runtime/music/acestep-1.5
host: 127.0.0.1
port: 8001
Gradio port: 8215
DiT: acestep-v15-xl-sft
LM: acestep-5Hz-lm-4B
backend: mlx
```

状态目录：

```text
~/AI/run/music/acestep-api/
```

日志：

```text
~/AI/logs/music/acestep-api.log
```

## 4. 命令

查看状态：

```bash
bash scripts/music_api_service.sh status
```

只检查 READY，不修改服务：

```bash
bash scripts/music_api_service.sh check-ready
```

确保服务 READY：

```bash
bash scripts/music_api_service.sh ensure
```

`ensure` 是幂等操作：

```text
READY        直接复用
HTTP_READY   调用 /v1/init
DEGRADED     调用 /v1/init 修正模型状态
DOWN         启动 REST API 并等待 READY
FAILED       停止并输出明确错误，不操作未知进程
```

停止：

```bash
bash scripts/music_api_service.sh stop
```

重启：

```bash
bash scripts/music_api_service.sh restart
```

查看日志：

```bash
bash scripts/music_api_service.sh logs 160
```

兼容旧入口：

```bash
bash scripts/start_music_api_macos.sh
bash scripts/status_music_api_macos.sh
bash scripts/stop_music_api_macos.sh
bash scripts/ensure_music_api_ready.sh
```

## 5. 安全策略

服务管理脚本遵守以下约束：

```text
不执行模型删除
不执行模型重新安装
模型目录存在时不主动下载重复权重
Gradio 8215 正在监听时拒绝新启 REST 服务
8001 被未知程序占用时拒绝抢占
stop 优先使用本项目 PID
发现未知监听进程时拒绝强杀
```

`stop` 只允许终止可识别为 ACE-Step API 的进程。

## 6. 启动策略

新启动服务时固定：

```text
ACESTEP_LM_BACKEND=mlx
ACESTEP_CONFIG_PATH=acestep-v15-xl-sft
ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-4B
ACESTEP_INIT_LLM=true
ACESTEP_NO_INIT=false
ACESTEP_DOWNLOAD_SOURCE=modelscope
```

优先 eager load。

如果服务器已经启动，但 health 显示模型未初始化，则使用：

```text
POST /v1/init
```

补齐 DiT 和 LM。

## 7. 稳定错误码

T1 服务层可能输出：

```text
PRECHECK_FAILED
SERVICE_START_FAILED
MODEL_INIT_FAILED
MODEL_NOT_READY
SERVICE_STOP_FAILED
```

调用方应优先读取 `ERROR_CODE=`，随后读取人类可读错误信息和日志尾部。

## 8. T1 验收

统一验收入口：

```bash
bash scripts/accept_music_api_service.sh
```

验收自动执行：

```text
记录当前状态
停止服务
确认 DOWN
从 DOWN 执行 ensure
确认 READY
再次执行 ensure
确认第二次直接复用 READY
检查最终模型状态
```

通过标志：

```text
T1_SERVICE_ACCEPTANCE_PASS
```

该验收会主动停止并重新加载一次 ACE-Step 模型，因此执行期间不要同时运行音乐生成任务或 Gradio UI。

## 9. 后续依赖

T1 通过后，T2 参考音频分析、T3 短片段准备、T4/T5 参数实验全部只依赖：

```text
bash scripts/music_api_service.sh ensure
```

后续抽取到 `shared/music/` 时保持命令语义不变，具体产品脚本只需要调用共享服务管理器。
