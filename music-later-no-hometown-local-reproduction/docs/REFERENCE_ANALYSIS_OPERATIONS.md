# T2 参考音频深度分析操作说明

状态：等待 multipart 修复后的本机重验  
适用任务：《后来没有故乡》  
适用分支：`feat/local-music-reproduction-v01`

## 目标

T2 只分析参考音频，不生成新歌曲。

输入：

```text
/Users/jerson/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav
```

工作 WAV SHA256：

```text
288edd5197a7535d9dadfac27dc1aea469999e16dc6dfeaf1291cc882afd6775
```

分析链路：

```text
工作 WAV
  ↓ SHA256 + ffprobe
T1 ensure_ready
  ↓
multipart 上传 src_audio
  ↓
ACE-Step full_analysis_only
  ↓
audio codes
  ↓
4B LM understand_audio_from_codes
  ↓
结构化分析结果
  ↓
限定路径 commit + push
```

## API 音频传输约束

当前固定的 ACE-Step 上游 commit：

```text
ca1e85fe9430179831e6bc6be790c332190a3866
```

该版本 `/release_task` 对音频路径执行安全校验。JSON 请求中的任意本机绝对音频路径如果位于系统临时目录之外，会返回：

```text
HTTP 400
absolute audio file paths are not allowed
```

因此 Job 仍保留本机绝对路径，用于本机校验、SHA256、ffprobe 和可复现记录；真正提交到 API 时采用：

```text
Content-Type: multipart/form-data
文件字段: src_audio
```

ACE-Step 接收上传后会把音频保存到系统临时目录，再把该临时路径交给内部任务。这样符合上游安全策略，也避免修改 ACE-Step 源码。

参考音频通过本机 `127.0.0.1` 上传给本机 ACE-Step 服务，不会因此上传到 Git。Git 仍然只保存 SHA256、技术元数据和分析结果。

后续 cover/remix 正式生成也使用相同传输规则。`music_job.py` 已同步支持：

```text
src_audio_path       -> multipart 字段 src_audio
reference_audio_path -> multipart 字段 reference_audio
无本地音频           -> application/json
```

## 首次验收发现的问题

2026-09-13 第一次 T2 正式验收已经通过以下 Gate：

```text
ACE-Step READY
工作 WAV SHA256
ffprobe
Job commit 记录
ACE-Step commit 记录
```

在 `/release_task` 提交阶段被上游安全策略拒绝：

```text
ERROR_CODE=API_SUBMIT_FAILED
HTTP 400 Bad Request
{"detail":"absolute audio file paths are not allowed"}
```

已经根据固定 commit 的上游源码确认原因，并将传输层修复为 multipart 文件上传。T2 当前需要重新执行本机验收。

## 正常验收命令

```bash
cd /Users/jerson/ai_video_product
git switch feat/local-music-reproduction-v01
git pull --ff-only origin feat/local-music-reproduction-v01
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh
```

成功提交后终端应先出现：

```text
transport=multipart/form-data
audio_field=src_audio
task_id=...
```

最终成功标志：

```text
REFERENCE_ANALYSIS_PASS
REFERENCE_ANALYSIS_PUBLISHED
REFERENCE_ANALYSIS_WORKFLOW_PASS
T2_REFERENCE_ANALYSIS_ACCEPTANCE_PASS
```

## 输出文件

```text
metadata/reference-analysis.latest.json
metadata/reference-analysis.latest.log
```

JSON 保存完整机器可读结果，包括：

```text
task_id
status
job SHA256
Job Git commit
ACE-Step commit
DiT / LM / backend
参考音频 SHA256
ffprobe 信息
API health 快照
request
transport
result
summary
```

`transport` 用于明确记录本次 API 的音频传输方式。

`summary` 重点提供：

```text
bpm
keyscale
timesignature
duration
genre
language
prompt
metas_present
audio_codes_present
audio_codes_length
```

完整 `audio_codes` 保存在 JSON 的 `result` 中，文本日志只记录摘要，控制 Git 日志体积。

## Git 安全边界

分析脚本只自动提交：

```text
music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.json
music-later-no-hometown-local-reproduction/metadata/reference-analysis.latest.log
```

本地其他脏文件不会被加入提交。当前两个历史视频 `final.mp4` 的删除状态不会被该脚本处理。

开始新分析前要求：

```text
local HEAD == origin/feat/local-music-reproduction-v01
```

用于保证分析快照能绑定到一个明确的代码版本。

## Git push 失败恢复

如果模型分析已经成功，只在 push 阶段失败，禁止重新执行模型分析。

执行：

```bash
bash music-later-no-hometown-local-reproduction/scripts/run_reference_analysis.sh publish-only
```

该命令只发布现有分析结果。

## 失败码

常见稳定错误码：

```text
WRONG_BRANCH
REMOTE_OUT_OF_SYNC
PRECHECK_FAILED
SOURCE_MISSING
REFERENCE_INVALID
MODEL_NOT_READY
API_SUBMIT_FAILED
API_POLL_FAILED
GENERATION_FAILED
RESULT_INVALID
GIT_COMMIT_FAILED
GIT_PUSH_FAILED
```

出现失败时保留终端输出，不需要手工修改分析结果。

## T2 验收条件

必须同时满足：

```text
ACE-Step READY
参考 WAV SHA256 正确
ffprobe 成功
multipart src_audio 提交成功
API task status=1
result 为对象
audio_codes 非空
metas 存在
分析文件成功 push
本地和 origin 分支 tip 一致
远端分析文件与本地一致
```

通过后进入 T3：参考歌曲短片段准备。
