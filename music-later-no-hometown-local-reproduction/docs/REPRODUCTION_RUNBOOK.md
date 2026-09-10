# 《后来没有故乡》本地复现 Runbook

状态：WORKFLOW READY / LOCAL EXECUTION PENDING

目标：在 Apple Silicon Mac 上使用 ACE-Step 1.5，对 Owner 已确认满意的参考歌曲进行本地近似复现，并逐步提高旋律、结构、男声音色、唱法、编曲和局部细节的一致性。

本流程优先保护现有 `local-ai-platform` 能力。任何步骤都不得为了让 ACE-Step 跑起来而关闭浏览器、IDE、ChatGPT/Codex、Unity 或其他正常工作程序。资源不足本身就是有效结果。

## 0. 已固定的输入

参考音频：

```text
后来没有故乡.m4a
SHA-256: 176c81b30cbd68de6cd7c900d1513160f9a6a591eb7e9bed65d848f273c48b0e
时长: 335.840 秒
采样率: 48000 Hz
声道: stereo
codec: Opus
```

ACE-Step 上游固定版本：

```text
repo: https://github.com/ACE-Step/ACE-Step-1.5.git
commit: ca1e85fe9430179831e6bc6be790c332190a3866
```

固定 commit 的原因是避免上游更新导致同一流程在不同日期行为变化。后续升级必须单独验证。

## 1. 同步仓库分支

如果本地已经有两个仓库：

```bash
cd ~/local-ai-platform
git fetch origin
git switch feat/local-music-reproduction-v01
git pull --ff-only

cd ~/ai_video_product
git fetch origin
git switch feat/local-music-reproduction-v01
git pull --ff-only
```

如果你的本地目录名称或路径不同，使用实际路径即可。

音乐运行时不会安装进这两个 Git 仓库。ACE-Step、模型、缓存和音频工作文件都放到独立目录。

## 2. 只读预检

进入任务目录：

```bash
cd ~/ai_video_product/music-later-no-hometown-local-reproduction
bash scripts/preflight_macos.sh
```

预检只读取：

- macOS 和 arm64 架构；
- `git`、`ffmpeg`、`ffprobe`、`shasum`、`lsof`；
- 当前物理内存、swap 和 memory pressure；
- Home 盘剩余空间；
- 8215 端口是否已被占用。

预检不会停止任何进程。

如果缺少 ffmpeg：

```bash
brew install ffmpeg
```

如果缺少 Git，可使用 Xcode command line tools 或 Homebrew Git。

## 3. 安装独立 ACE-Step 运行时

执行：

```bash
bash scripts/bootstrap_acestep_macos.sh
```

默认安装位置：

```text
~/AI/runtime/music/acestep-1.5
```

脚本会：

1. 安装 `uv`，仅在系统还没有时执行；
2. clone ACE-Step 到独立 music runtime；
3. checkout 固定 commit；
4. 在 ACE-Step 自己的目录创建独立 `.venv`；
5. 执行 `uv sync`；
6. 创建私有 reference 和 output 目录。

不会修改现有 Qwen/oMLX、Whisper、TTS、FLUX、LongCat 或 RAG Python 环境。

安装完成后应看到：

```text
BOOTSTRAP_PASS
```

## 4. 准备参考歌曲

假设 Suno 下载文件在 Downloads：

```bash
bash scripts/prepare_reference.sh "$HOME/Downloads/后来没有故乡.m4a"
```

脚本首先校验 SHA-256。只有与当前确认的满意版本完全一致才继续。

成功后本地会得到：

```text
~/AI/private/music-source/later-no-hometown/后来没有故乡.m4a
~/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav
~/AI/private/music-source/later-no-hometown/后来没有故乡.ffprobe.json
~/AI/private/music-source/later-no-hometown/后来没有故乡.sha256
```

WAV 只是工作格式转换，不能把原始有损 M4A 恢复成无损母带。它的用途是提高本地音频工具兼容性。

## 5. 先跑 Smoke，不直接上 XL

启动：

```bash
bash scripts/launch_acestep_macos.sh smoke
```

Smoke profile：

```text
DiT: acestep-v15-turbo
LM:  acestep-5Hz-lm-0.6B
backend: MLX
bind: 127.0.0.1
port: 8215
batch: 1
```

首次运行会下载模型，因此时间取决于网络。

打开：

```text
http://127.0.0.1:8215
```

只做一个 20 到 30 秒的简单生成，确认：

- UI 正常打开；
- MLX backend 正常；
- 能生成并播放音频；
- 浏览器和现有 AI 服务仍正常；
- 没有不可接受的 swap/memory pressure。

完成后在启动 ACE-Step 的终端按：

```text
Ctrl+C
```

因为运行方式是前台进程，这只停止当前 ACE-Step，不需要 PID 扫描或 kill 其他程序。

## 6. 第一轮真实复现：repro profile

执行：

```bash
bash scripts/preflight_macos.sh
bash scripts/launch_acestep_macos.sh repro
```

Repro profile：

```text
DiT: acestep-v15-xl-turbo
LM:  acestep-5Hz-lm-1.7B
backend: MLX
batch: 1
```

这个阶段的目标是找到最接近原参考的路线，再考虑更重的 `quality` profile。

## 7. 先做 Audio Understanding

在 ACE-Step UI 中，对本地 reference WAV 做分析，记录：

```text
BPM
Key / Scale
Time Signature
Caption / style description
可用的语义 codes
```

当前 prompt 中的 `68 BPM` 只是创作时的 hint。复现时应优先采用 ACE-Step 从最终参考音频中识别出的实际结果。

把分析结果记入一次运行记录，后续所有候选尽量复用同一组 metadata。

## 8. 路线 A：Custom + Reference Audio

目的：先复现整体音色、男声气质、配器和情绪，不强求旋律完全一致。

UI 操作：

1. Generation Mode 选择 `Custom`；
2. Caption 粘贴 `generated/style.txt`；
3. Lyrics 粘贴 `generated/lyrics.txt`；
4. Reference Audio 上传本地 reference WAV；
5. Vocal Language 选择中文或 auto/unknown；
6. BPM、Key、Time Signature 优先填写第 7 步分析结果；
7. Audio Duration 设置接近 `335.84` 秒；
8. Batch Size 保持 1；
9. 首轮保持默认推理参数；
10. 输出格式优先 `wav` 或 `flac`。

先生成 2 到 4 个不同 seed 的候选，不要一次把 batch 拉高。每次只跑 1 个对资源更友好。

判断维度：

- 年轻男声是否保留疲惫、低中音区、略含糊吞尾音；
- 中文歌词是否清楚；
- 主歌是否接近低声叙述；
- 副歌是否克制，没有突然英雄式爆发；
- 钢琴、木吉他、刷鼓、大提琴的比例是否接近；
- 结尾是否保持未完全解决的无力感。

这一阶段得到的是“同一首歌气质的另一个录音版本”。

## 9. 路线 B：Remix，作为主要近似复刻路线

ACE-Step 当前 UI 把保持源音乐结构的 cover/variant 工作流放在 `Remix` 模式。

操作：

1. Generation Mode 选择 `Remix`；
2. Source Audio 上传完整 `后来没有故乡.reference-48k.wav`；
3. Caption 使用 `generated/style.txt`；
4. Lyrics 使用 `generated/lyrics.txt`；
5. 先保持 reference 分析出的 BPM/Key 信息；
6. 输出 WAV；
7. Batch Size = 1。

### Remix Strength 扫描

上游文档说明 Remix Strength 越高，越接近源音频结构。

建议首轮固定其他参数，依次测试：

```text
0.70
0.85
0.95
```

每个 strength 至少试 2 个 seed。

评估时优先级：

```text
1. 主旋律和段落长度
2. 关键歌词落点
3. 男声音色与唱法
4. 和声/和弦进行
5. 配器细节
6. 混音和空间感
```

如果 0.95 产生明显伪影或过度粘连源音频，回到 0.85。

## 10. Seed 选择方法

当 strength 基本确定以后，只改变 seed。

建议一次记录 4 到 8 个 seed，但仍串行生成，避免同时占用过多统一内存。

对每个候选保留：

```text
seed
profile
DiT
LM
mode
remix strength
BPM
Key
Duration
reference SHA-256
output SHA-256
主观评分
问题时间点
```

可复制 `metadata/candidate.template.json` 作为每次候选记录模板。

如果某个结果整体最接近，只在它上面继续 Repaint，不要重新随机整首。

## 11. Repaint 局部修复

适用情况：

- 某一句中文咬字错误；
- 某一处男声突然变得太老或太亮；
- “三块钱”等关键歌词落点不满意；
- 某个副歌突然过强；
- 某个乐器在一小段里抢得太多；
- 结尾没有收下来。

操作：

1. Generation Mode 选择 `Repaint`；
2. Source Audio 使用当前最佳本地候选；
3. 设置 Repainting Start/End；
4. Caption 只描述这段需要保留或修正的特征；
5. 每次修复尽量控制在短区间；
6. 修完立即试听前后衔接。

不要为了一个 10 秒问题重生成整首。

## 12. 可选：截取更强的 Reference Audio

如果 Custom 模式用整首 reference 对音色控制不稳定，可以从最能代表人声和配器的一段副歌截 20 到 40 秒。

例：

```bash
START=120
DURATION=30
SRC="$HOME/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav"
OUT="$HOME/AI/private/music-source/later-no-hometown/chorus-reference.wav"

ffmpeg -y -ss "$START" -t "$DURATION" -i "$SRC" -c:a pcm_s16le "$OUT"
```

先人工确认该区间确实包含你最满意的人声和伴奏，再使用。

## 13. 什么时候尝试 quality profile

只有在 `repro` 已经：

- 能稳定启动；
- 已生成完整 5 分多钟候选；
- 正常工作应用仍在运行；
- 没出现不可接受的 memory pressure/swap；
- 你确认 XL 的质量提升值得继续；

再执行：

```bash
Ctrl+C
bash scripts/preflight_macos.sh
bash scripts/launch_acestep_macos.sh quality
```

Quality profile：

```text
DiT: acestep-v15-xl-sft
LM:  acestep-5Hz-lm-4B
```

如果这里资源压力明显：

```text
STOP
记录 RESOURCE_BLOCKED
继续使用 repro profile
```

不要关闭正常应用来让 quality profile 通过。

## 14. 暂时不要训练 LoRA

当前目标只有一首参考歌。ACE-Step 支持 LoRA，但单首作品不足以定义稳定的个人音乐风格数据集。

优先顺序应为：

```text
Reference Audio
-> Remix
-> seed selection
-> Repaint
-> 多首自有作品积累后再考虑 LoRA
```

LoRA 是后续风格长期复用方案，不是第一轮复刻的必要条件。

## 15. 现有能力回归检查

ACE-Step 运行前后，至少确认：

- 原有 Qwen 服务端口和健康状态不因该脚本被修改；
- 没有脚本调用 `pkill`、`killall` 或扫描式 kill；
- 现有浏览器、IDE、ChatGPT/Codex 保持运行；
- 音乐运行时只位于 `~/AI/runtime/music/`；
- reference 只位于 `~/AI/private/music-source/`；
- 公共 Git tree 内没有 `.m4a/.wav/.mp3` reference 或未批准 master；
- ACE-Step 停止后 8215 不再监听。

可以检查：

```bash
lsof -nP -iTCP:8215 -sTCP:LISTEN || true
```

## 16. 输出管理

建议本地候选目录：

```text
~/AI/runtime/music/output/later-no-hometown/
```

文件命名建议：

```text
candidate-remix-s085-seed12345.wav
candidate-remix-s095-seed67890.wav
candidate-repaint-001.wav
```

最终选中的候选先保留本地，并计算：

```bash
shasum -a 256 final-candidate.wav
```

只有 Owner 明确批准发布这个 exact hash 后，才进入 public product publish gate。

## 17. 失败和回滚

安装阶段失败：保留错误日志，不动其他服务，修 ACE-Step 自己的环境。

生成阶段资源不足：在前台终端 `Ctrl+C` 停止 ACE-Step，记录资源状态。不要杀其他模型或用户应用。

想彻底撤销本次实验时，先确认 ACE-Step 已停止，然后可以删除它自己的 runtime 和私有 working copy：

```bash
rm -rf "$HOME/AI/runtime/music/acestep-1.5"
rm -rf "$HOME/AI/runtime/music/output/later-no-hometown"
```

参考源目录默认不要删除：

```text
~/AI/private/music-source/later-no-hometown
```

如需删除参考源，也要单独人工确认。

## 18. 成功标准

第一阶段成功不要求和 Suno 源文件逐波形一致。

M1 建议目标：

```text
歌词完整度: 高
段落/时长: 明显接近 reference
主旋律: 可辨认为同一首或高度近似的版本
人声角色: 年轻、疲惫、低中音区、略吞尾音
关键情绪: 克制、怀念、后悔、无力
编曲: 钢琴/木吉他/刷鼓/低音/大提琴同类结构
局部缺陷: 可以通过 Repaint 修复
```

如果 Remix 能做到整体接近但人声始终差异较大，这是正常的下一阶段问题。再考虑更精细的 voice/style reference、stem 辅助、或在拥有足够自有训练素材后使用 LoRA。
