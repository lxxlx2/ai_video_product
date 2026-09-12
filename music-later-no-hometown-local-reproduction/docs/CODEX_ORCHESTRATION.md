# Codex 驱动的本地音乐编排

状态：目标架构已确定，等待 `codex-web-bridge` 稳定后接管执行。

## 最终体验

目标是让用户只负责方向确认和最终审核。

```text
用户描述歌曲主题
  ↓
Codex 与用户讨论歌词和风格
  ↓
Codex 写 generated/lyrics.txt
  ↓
Codex 写 generated/style.txt
  ↓
Codex 写 jobs/current.json
  ↓
Codex 执行本地音乐脚本
  ↓
ACE-Step REST API 生成候选
  ↓
Codex 检查技术结果和日志
  ↓
Git review/latest
  ↓
用户试听并批准或要求修改
  ↓
Codex 固化准确候选
  ↓
Git LFS push + 远端验证
  ↓
Codex 清理中间产物
```

正常任务里用户无需操作 ACE-Step 网页。

## 和 codex-web-bridge 的边界

`codex-web-bridge` 负责 Codex 模型侧的稳定能力和会话/工具执行通路。

音乐生成保持为独立本机能力：

```text
Codex Desktop / CLI
  ↓
本地 shell / Python
  ↓
ai_video_product 中的音乐脚本
  ↓
ACE-Step REST API
  ↓
本地模型
```

音乐逻辑不写入 bridge 内部。这样 bridge 升级、模型切换、音乐模型升级可以分别演进。

## 当前阶段

当前先由 ChatGPT 负责“配置编排”，用户负责执行命令：

```text
ChatGPT 更新 Git 中的 job
  ↓
用户 pull
  ↓
用户执行 run_current_music_job.sh
  ↓
脚本自动 push review
  ↓
ChatGPT 从 Git 检查
```

这个阶段的目的就是把后续 Codex 要执行的动作完全脚本化。

## Codex 未来只需要理解三个东西

### 1. 歌曲需求

```text
主题
歌词
风格
长度
人声
参考音频（可选）
需要保留或改变的结构
```

### 2. job JSON

`jobs/current.json` 是执行契约。

Codex 可以修改其中的 ACE-Step request 字段，但每次长任务前要先完成参数检查，再将：

```json
"ready_to_run": true
```

### 3. review 结果

Codex 读取：

```text
review/latest/request.json
review/latest/result.json
review/latest/run.json
review/latest/runner.log
review/latest/server.log
review/latest/review.mp3
```

重点检查：

```text
API 是否成功
模型是否符合 job
seed
时长
candidate SHA-256
是否静音或明显截断
日志是否异常
用户关注的音乐问题
```

## 候选策略

默认不一次并行生成大量候选。

建议：

```text
一轮 1 首
  ↓
快速判断路线是否正确
  ↓
路线正确后再扫 2 到 4 个 seed
  ↓
保留最优候选
  ↓
局部问题使用 repaint
```

这台 Mac 使用统一内存。串行候选更容易控制内存，也更方便把每个 run 与 review commit 对应起来。

## 自动评分边界

Codex 可以自动检查：

```text
文件可播放
时长
采样率
静音比例
严重削波
输出是否截断
歌词是否有明显缺失
模型和参数是否正确
```

音乐好不好听、情绪是否对、人声是否符合预期，最终由用户判断。

## 审批契约

批准需要绑定：

```text
run_id
candidate_sha256
```

批准后才允许把本机候选提升为：

```text
output/final.wav
```

如果后续重新生成，即使文件名相同，SHA-256 变化后也需要重新批准。

## Git 自动化边界

Codex 自动执行时只能提交自己负责的路径。

音乐 review：

```text
<task>/review/latest
```

音乐 final：

```text
<task>/output/final.wav
```

任何时候都不能使用无范围的：

```text
git add .
git add -A
```

因为仓库里可能同时存在其他视频或用户手动修改。

## 最终保留策略

任务完成后长期保留：

```text
Git 中的 README / docs / metadata
最终歌词和 style
必要配置
output/final.wav
最终审核/发布信息
```

本机长期保留一份最终 master：

```text
~/AI/final/music/<song-slug>/final.wav
```

可以清理：

```text
失败候选
旧 review 本地副本
临时转码
stem
repaint 片段
一次性日志缓存
```

共享 ACE-Step 权重和 runtime 在音乐能力仍使用期间保留。

## 原创歌曲

参考复现只是第一条验证任务。

之后原创流程可以直接：

```text
用户给主题
  ↓
Codex 写歌词
  ↓
用户确认
  ↓
Codex 写 style/job
  ↓
ACE-Step text2music
  ↓
review
  ↓
批准
```

不需要 Suno 参考音频。

## 参考复现

```text
用户给参考
  ↓
Codex 校验 hash
  ↓
分析参考
  ↓
生成结构化 cover/repaint job
  ↓
候选
  ↓
review
  ↓
参数迭代
  ↓
批准
```

## 实施阶段

### Phase 1

```text
ACE-Step 安装和 MLX 验证
```

已完成。

### Phase 2

```text
REST API + 单 job runner + Git review
```

正在执行。

### Phase 3

```text
finalize + Git LFS + 清理
```

等 Phase 2 首轮真实运行通过后实现。

### Phase 4

```text
抽取 shared/music 通用能力
```

### Phase 5

```text
Codex 全程自动执行
```

等待 `codex-web-bridge` 稳定后接入。

## 非目标

本音乐工作流无需依赖旧 Qwen 常驻服务，也无需让多个大模型同时驻留内存。

当前设计同样不要求修改 ChatGPT Web、浏览器自动化协议或 bridge 的对话传输格式。