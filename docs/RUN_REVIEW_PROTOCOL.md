# 生成运行与 Git 审阅协议

## 当前工作方式

在 Codex 完全接管本地执行以前，采用下面的固定流程：

```text
1. 用户与 ChatGPT 讨论创作方向
2. ChatGPT 更新 Git 中的 job 配置、歌词或 style
3. 用户本机 git pull
4. 用户执行固定命令
5. runner 调本地生成模型
6. runner 保存日志、请求、API 响应、技术元数据和试听文件
7. runner 自动 commit + push
8. ChatGPT 从 Git 检查本次 run
9. 用户试听 preview.mp3
10. 决定继续调参、局部修复或批准
```

后期 Codex 只替代第 3 至第 7 步的人工触发，协议保持不变。

## 每次运行必须留下什么

成功和失败 run 都保留记录。

成功 run：

```text
request.json             实际提交的参数，敏感本机路径会做 ~ 化
release-response.json    /release_task 原始响应
final-response.json      /query_result 最终响应
run.log                  runner 时间线
manifest.json             run-id、模型、hash、时长、状态等摘要
ffprobe.json              结果音频技术参数
preview.mp3               Git 审阅文件
```

失败 run 至少保留：

```text
request.json
run.log
release-response.json     如果已提交
final-response.json       如果服务返回失败
manifest.json
```

失败 run 也要 push，以便远程诊断时可以直接读取证据。

## 本地高质量文件

runner 默认把 API 返回的原始音频存入：

```text
.work/<product>/<run-id>/result.<format>
```

`.work/` 不进入 Git。

如果原始结果为 WAV，runner 使用 ffmpeg 生成：

```text
runs/<run-id>/preview.mp3
```

用于 Git 审阅。

## 用户批准

用户批准时必须指定一个明确的 run-id。

例如：

```text
批准 20260912-183501-r004
```

之后 promotion 流程校验：

1. 本地原始音频 SHA-256 与 manifest 一致；
2. 复制到 `output/final.*`；
3. 记录 `approved_run_id`；
4. Git LFS commit + push；
5. 远端验证完成后才允许清理对应 `.work`。

当前阶段 promotion 可以人工执行，后续增加 `promote_run.py`。

## Git 审阅约定

ChatGPT 检查 run 时优先读取：

```text
manifest.json
request.json
run.log
final-response.json
```

用户负责实际听感判断。模型或自动评分只能作为辅助，不替代用户最终听感。

## 调参原则

每一轮尽量只改变少量变量，这样 run 之间才有比较意义。

推荐在 manifest 中记录 `parent_run_id`，形成：

```text
r001
  -> r002 调 cover strength
      -> r003 换 seed
          -> r004 Repaint 某段
```

避免一次同时修改歌词、style、seed、cover strength、BPM、调性和模型，导致无法知道改善来自哪里。

## Git 体积控制

默认每个 run 上传 MP3 试听文件，不上传完整 WAV。

原因：Git LFS 历史对象不会因为后续删除文件就自动消失，连续保存大量 WAV 会快速增长。

以下情况可以上传完整音频：

- 用户明确要求保留某个候选；
- 候选已经批准成为 final；
- 需要定位编码或后处理问题，MP3 无法复现；
- job 显式设置 `review.publish_full_audio=true`。

## 私有参考音频

参考歌曲不自动上传 Git。

Git 里只记录：

```text
文件用途
SHA-256
时长
采样率
codec
本机路径模板
```

真实文件继续位于 `~/AI/private/`。