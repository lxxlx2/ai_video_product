# T2 参考音频深度分析操作说明

状态：待本机验收  
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

## 正常验收命令

```bash
cd /Users/jerson/ai_video_product
git switch feat/local-music-reproduction-v01
git pull --ff-only origin feat/local-music-reproduction-v01
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_analysis.sh
```

成功标志：

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
result
summary
```

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
API task status=1
result 为对象
audio_codes 非空
metas 存在
分析文件成功 push
本地和 origin 分支 tip 一致
远端分析文件与本地一致
```

通过后进入 T3：参考歌曲短片段准备。
