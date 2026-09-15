# 产物工作流

## 总流程

仓库统一采用下面的产品生命周期：

```text
需求讨论
  ↓
结构化配置
  ↓
本地执行
  ↓
生成候选
  ↓
技术检查
  ↓
Git review 快照
  ↓
人工审核
  ↓
继续迭代或批准
  ↓
最终文件固化
  ↓
Git/LFS 推送并远端验证
  ↓
清理中间产物
```

## 当前阶段

当前音乐任务仍由 ChatGPT 与用户共同决定歌词、风格和参数。ChatGPT 将配置写入 Git，用户只需要同步分支并执行约定命令。

运行结束后脚本自动生成 review 快照并 push 到 Git。用户告知运行完成后，ChatGPT 直接读取 Git 中的请求、日志、结果摘要和试听文件信息进行判断。

后续 `codex-web-bridge` 稳定后，Codex 接管以下步骤：

```text
读取需求
生成/修改歌词
生成 style
写 current.json
执行任务
等待结果
技术检查
上传 review
等待用户批准
最终固化
清理
```

用户保留最终审核权。

## 音乐 review 契约

每次运行至少记录：

```text
run_id
开始/结束时间
ACE-Step commit
DiT 模型
LM 模型
task_type
完整生成参数
seed
参考音频 SHA-256
候选 WAV SHA-256
候选时长
API 返回结果
runner 日志
服务日志片段
Git review.mp3
```

review 目录固定：

```text
<task>/review/latest/
```

这样 ChatGPT 或 Codex 每次只需检查一个位置。

## 审核与最终固化

用户批准必须绑定到一个明确的 `candidate_sha256`。

最终固化脚本需要验证本机候选 SHA-256 与批准记录一致，然后执行：

```text
candidate.wav
  ↓ SHA-256 再验证
output/final.wav
  ↓ Git LFS
push
  ↓
远端存在性验证
```

完成远端验证以后，该任务的其他大体积候选才允许删除。

## 失败策略

运行失败时也要上传轻量日志和请求摘要。review 快照标记：

```text
status: failed
```

失败运行不生成或覆盖 `output/final.*`。

如果 API 服务无法启动、模型缺失、参考文件 SHA 不一致、磁盘空间不足、端口冲突，脚本直接停止并给出明确错误。

## Git 提交边界

自动脚本只能提交自己的 review 路径。

禁止使用：

```text
git add -A
git add .
```

因为本地工作树可能存在其他视频、图片或用户手动修改。

允许：

```text
git add <task>/review/latest
```

自动 commit 也必须限制到该路径。

## 大文件策略

审核阶段：

```text
本地保留 WAV
Git 上传 MP3 preview + JSON + log
```

批准阶段：

```text
Git/LFS 上传 final.wav
```

这样能够让远端审核足够方便，同时控制 LFS 存储和历史增长。
