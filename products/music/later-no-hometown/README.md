# 《后来没有故乡》本地音乐项目

这个目录用于《后来没有故乡》的本地生成、参考复现、参数实验和最终产物归档。

当前目标有两层：

1. 尽可能复现已经满意的 Suno 版本，用它验证本地参考音频工作流；
2. 把整个流程抽象成通用能力，后续可以只通过歌词和风格描述在本地创作新歌。

## 当前结论

截至 2026-09-12：

```text
Mac / Apple Silicon 预检                 PASS
ACE-Step 1.5 独立运行时                  PASS
XL SFT 模型下载与校验                    PASS
4B LM 下载与校验                         PASS
MLX DiT                                  PASS
MLX VAE                                  PASS
30 秒本地生成                            PASS
下载缓存和残片清理                       PASS
第一次 30 秒 Custom 听感                 REJECTED
第一次完整 5:36 Remix/Cover 听感         REJECTED
命令行 REST 自动化                       IMPLEMENTED / 待本机验收
Git run 审阅协议                          IMPLEMENTED / 待本机验收
```

两个生成结果在技术上都完成了，但音乐听感无法接受，因此它们只证明运行时可用，没有证明 ACE-Step 当前参数已经达到目标质量。

## 当前技术栈

运行时：

```text
~/AI/runtime/music/acestep-1.5
```

固定上游 commit：

```text
ca1e85fe9430179831e6bc6be790c332190a3866
```

当前质量模型：

```text
DiT: acestep-v15-xl-sft
LM:  acestep-5Hz-lm-4B
backend: MLX
```

模型安装后正式 checkpoint 总量约 36G。

## 参考歌曲

原始参考音频只保存在本机私有目录，不上传 Git。

已确认源信息：

```text
文件名: 后来没有故乡.m4a
时长: 335.840 秒
采样率: 48000 Hz
声道: stereo
codec: Opus
sha256: 176c81b30cbd68de6cd7c900d1513160f9a6a591eb7e9bed65d848f273c48b0e
```

本地工作参考：

```text
~/AI/private/music-source/later-no-hometown/后来没有故乡.reference-48k.wav
```

## 已确认的问题

### 30 秒 Custom

模型成功生成了中文歌曲，但自动 LM 规划把带有 `minor key` 的描述规划成了 `G major`，并且人声旋律、音准和整体听感都不符合要求。

因此后续受控实验默认：

```text
thinking: false
use_cot_caption: false
use_cot_language: false
```

需要自动规划时再单独开启。

### 完整 Remix/Cover

第一次完整 5:36 参考复现也被人工试听否决。

这说明“模型能接收参考音频”与“可以高质量复刻目标歌曲”是两个不同验收项。后续继续实验时必须保存每一轮真实参数和结果，避免通过 UI 猜测状态。

## 新的工作方式

从现在开始，正常实验不再依赖 Gradio 手工填写。

固定流程：

```text
ChatGPT 与用户讨论本轮参数
        ↓
更新 config/next-run.json
        ↓
用户执行一条命令
        ↓
ACE-Step REST API 本地生成
        ↓
runner 保存原始结果到 .work
        ↓
runner 生成 preview.mp3
        ↓
runner 保存 request / response / log / manifest
        ↓
自动 Git commit + push
        ↓
ChatGPT 从 Git 检查日志和配置
用户试听 preview.mp3
        ↓
决定下一轮参数
```

未来 Codex 接管以后，仍然执行相同 runner，只把人工执行命令替换成 Codex 本地工具调用。

通用脚本位于：

```text
workflows/music/ace-step/
```

仓库级协议：

```text
docs/RUN_REVIEW_PROTOCOL.md
docs/REPOSITORY_STRUCTURE.md
```

## 项目目录

```text
products/music/later-no-hometown/
├── README.md
├── source/             参考音频说明，不含私有原音频
├── generated/          当前歌词和 style
├── config/             项目配置和 next-run.json
├── runs/               每轮 Git 审阅记录
├── output/             最终批准产物
├── metadata/           长期技术记录
└── docs/               历史 runbook、进度和决策
```

## 每轮 Run

每次 API 生成后，Git 中出现：

```text
runs/<run-id>/
├── request.json
├── release-response.json
├── final-response.json
├── run.log
├── manifest.json
├── ffprobe.json
└── preview.mp3
```

原始 WAV 默认保存在：

```text
<repo>/.work/products/music/later-no-hometown/<run-id>/result.wav
```

这样 Git 可以保存所有可审阅的实验记录，又不会因为每轮上传大型 WAV 快速消耗 LFS。

## 最终产物

只有用户明确批准的 run 才提升为：

```text
output/final.wav
```

批准必须绑定具体 run-id 和 SHA-256。

## 当前下一步

先验证新的命令行链路本身：

```text
1. 切换到 feat/product-layout-v04
2. 停止当前 Gradio
3. 启动或自动启动 127.0.0.1:8001 REST API
4. 执行 config/next-run.json
5. 确认 runs/<run-id>/ 自动生成并 push
6. ChatGPT 从 Git 检查日志
7. 用户试听 preview.mp3
```

命令行链路验证通过后，再继续做参数搜索。这样后面的每一次失败都有可比较的证据。