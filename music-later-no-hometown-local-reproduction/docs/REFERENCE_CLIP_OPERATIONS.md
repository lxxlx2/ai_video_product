# T3 参考歌曲短片段准备

状态：等待本机验收  
适用任务：《后来没有故乡》  
适用分支：`feat/local-music-reproduction-v01`

## 目标

T3 从已经通过 T2 的完整参考 WAV 中自动准备 20 到 45 秒的短片段，用于 T4/T5 参数实验。

本阶段不调用 ACE-Step 生成音乐，不修改歌词，也不把参考音频提交到 Git。

## 输入

完整工作 WAV：

```text
/Users/jerson/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav
```

SHA256：

```text
288edd5197a7535d9dadfac27dc1aea469999e16dc6dfeaf1291cc882afd6775
```

T2 分析结果：

```text
metadata/reference-analysis.latest.json
```

当前技术参考：

```text
BPM=130
Key=B♭ major
Time Signature=4/4
Duration=336s
Genre=Chinese folk-pop
```

130 BPM 仍可能对应约 65 BPM 的 half-time 听感。T3 只记录该值，不直接把它固化为后续生成参数。

## 自动选择策略

配置：

```text
jobs/reference-clip.json
```

默认片段时长：

```text
32 秒
```

自动扫描会排除歌曲最前和最后各 24 秒，然后每 2 秒评估一个候选窗口。

`energy_transition_v1` 使用低采样率单声道代理音频计算每秒 RMS，候选排序考虑：

```text
45% 片段后段相对前段的能量抬升
25% 持续活动程度
20% 音量稳定性
10% 靠近歌曲中部的轻微偏好
```

这个规则用于寻找更可能包含主歌到副歌过渡、稳定人声和主要伴奏的区域。

它只是确定性的工程启发式算法，不能代替音乐审美判断。

## 输出

本地私有目录：

```text
~/AI/private/music-source/later-no-hometown/clips/
```

默认生成三个候选：

```text
reference-candidate-01.wav
reference-candidate-02.wav
reference-candidate-03.wav
```

排名第一的候选作为当前 `selected`，后续 T4 实验默认使用它。

Git 只保存：

```text
metadata/reference-clip.latest.json
```

该 JSON 包含：

```text
source SHA256
T2 analysis SHA256 / task_id
选择策略
三个候选的 start/duration/score/path/SHA256
selected 候选
Job commit
```

音频文件继续只保存在本机 private 目录。

## 正常验收

执行：

```bash
cd /Users/jerson/ai_video_product
git switch feat/local-music-reproduction-v01
git pull --ff-only origin feat/local-music-reproduction-v01
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_clip_prepare.sh
```

成功时应看到：

```text
REFERENCE_CLIP_PREPARE_PASS
REFERENCE_CLIP_PUBLISHED
LOCAL_REFERENCE_CLIPS_VALID=true
REMOTE_CLIP_METADATA_VERIFIED=true
T3_REFERENCE_CLIP_ACCEPTANCE_PASS
```

终端会列出三个候选的起点、时长、分数和本地文件路径。

## Git push 失败恢复

如果三个 WAV 已经成功生成，只在 Git push 阶段失败：

```bash
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_clip_prepare.sh publish-only
```

该模式不会重新切片，只发布现有 `reference-clip.latest.json`。

如果发布已经完成，只需要重新验收：

```bash
bash music-later-no-hometown-local-reproduction/scripts/accept_reference_clip_prepare.sh verify-only
```

## 安全边界

T3 不会：

```text
提交参考 WAV
提交三个候选 WAV
调用 ACE-Step 生成歌曲
删除任何模型
修改两个历史视频 final.mp4 状态
使用 git add .
使用 git add -A
```

T3 只自动提交固定路径：

```text
music-later-no-hometown-local-reproduction/metadata/reference-clip.latest.json
```

## T3 通过后

进入：

```text
T4 experiment job
T5 short cover experiment
```

T4 会读取 `selected.path` 和 `selected.sha256` 建立短片段实验任务。T5 首轮只调整少量明确变量，先确认旋律、中文人声、节奏和参考保持程度，再考虑完整歌曲。
