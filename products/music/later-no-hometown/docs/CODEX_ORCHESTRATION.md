# Codex 音乐自动化规划

状态：`运行接口已固定 / Codex 自动执行待 codex-web-bridge 稳定`

## 最终目标

用户只负责：

```text
创作讨论
试听
批准
```

Codex 负责：

```text
维护歌词和 style
维护 next-run.json
启动或检查 ACE-Step API
执行 runner
等待生成
检查日志和技术指标
把 run push 到 Git
根据用户反馈修改下一轮
批准后提升 final
验证 Git LFS
清理本地中间文件
```

## 固定调用边界

Codex 不需要修改 `codex-web-bridge` 协议来支持音乐。

目标路径：

```text
Codex Desktop / CLI
-> 本地 shell 工具
-> ai_video_product/workflows/music/ace-step/run_and_publish.sh
-> ACE-Step REST API 127.0.0.1:8001
-> 本地 MLX 模型
```

因此当前人工阶段和未来 Codex 阶段使用同一套脚本。

## 当前阶段

```text
ChatGPT 改 Git 配置
用户执行命令
runner 自动 push
ChatGPT 查 Git
用户试听
```

这是 Codex 最终形态的人工触发版本。

## 未来阶段

当 `codex-web-bridge` 的 standalone / desktop 执行链稳定后：

```text
用户：把副歌再压抑一点
        ↓
Codex 修改 style / next-run.json
        ↓
Codex 执行 run_and_publish.sh
        ↓
等待 run 完成
        ↓
Codex 读取新 run 的 manifest / log / response
        ↓
Codex 告诉用户新候选已就绪
        ↓
用户试听 preview.mp3
```

无需浏览器点 ACE-Step UI。

## Job 是 Codex 和生成模型之间的正式合同

示例：

```json
{
  "request": {
    "model": "acestep-v15-xl-sft",
    "task_type": "cover",
    "prompt_file": "generated/style.txt",
    "lyrics_file": "generated/lyrics.txt",
    "thinking": false,
    "vocal_language": "zh",
    "audio_duration": 335.84,
    "inference_steps": 50,
    "audio_format": "wav"
  }
}
```

Codex 只能通过修改明确字段调参，避免 UI 隐藏状态。

## Run 是审计单位

每次执行产生唯一 run-id。

Codex 判断下一轮时读取：

```text
request.json
manifest.json
run.log
final-response.json
```

用户的主观反馈绑定具体 run-id，例如：

```text
20260912-183501 人声太老
20260912-190240 旋律接近，但副歌太用力
```

下一轮用 `parent_run_id` 指向上一轮，形成实验链。

## 自动技术检查

后续可以由 Codex 自动判断：

```text
生成是否成功
文件是否可解码
时长是否正确
是否出现长时间静音
是否严重削波
采样率/声道
SHA-256
配置差异
```

音乐是否好听、情绪是否正确，最终仍由用户决定。

## 批量策略

默认保持：

```text
batch_size = 1
```

因为 M4 Max 48GB 使用统一内存，串行候选更稳定，也便于每个 run 独立审阅。

后续若需要 seed 搜索，Codex 应有限执行，例如最多 3 至 4 个候选，再让用户选择，避免无限生成。

## 批准 Gate

用户批准必须指向具体 run-id。

批准后 Codex：

1. 校验本地原始结果 SHA-256；
2. 复制到 `output/final.wav`；
3. 写入批准 metadata；
4. Git LFS commit + push；
5. 验证远端；
6. 再清理 `.work` 中已无价值的中间文件。

## 当前尚未实现

```text
promote_run.py
自动音频质量检查
参数 sweep 控制器
Codex 自动执行触发
最终远端 LFS 校验自动化
```

优先级：先完成 runner 的第一次真实本机验收，再逐项增加。