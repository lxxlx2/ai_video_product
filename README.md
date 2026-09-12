# AI 生成产物仓库

这个仓库用于保存经过审核的 AI 生成产物，以及为了稳定复现这些产物所需的脚本、配置、日志和说明文档。

当前覆盖三类产物：视频、音乐/音频、其他未来产物。仓库同时承担“结果归档”和“可复现流程记录”两个职责，但模型权重、缓存、私有参考素材和大量临时中间文件继续保留在本机运行目录，不进入 Git。

## 一、仓库分类

长期目标结构如下：

```text
ai_video_product/
├── README.md
├── .gitattributes
├── docs/
│   ├── REPOSITORY_STRUCTURE.md
│   └── PRODUCT_WORKFLOW.md
├── products/
│   ├── video/
│   ├── music/
│   └── other/
├── shared/
│   ├── music/
│   ├── video/
│   └── common/
└── <兼容期旧任务目录>/
```

含义：

```text
products/video/   已审核的视频产品任务
products/music/   已审核或正在审核的歌曲、音频任务
products/other/   未来图片、数据制品、交互产物等
shared/           多个任务可复用的脚本、模板和通用流程
docs/             仓库级架构、约定、迁移和发布说明
```

目前仓库里已经存在两个 Solana University 视频目录，以及 `music-later-no-hometown-local-reproduction` 音乐目录。为了避免当前本地工作区存在删除状态时触发路径迁移冲突，这三个旧目录暂时保留原路径。当前音乐验证完成、本地工作区干净后，再统一迁移到 `products/` 分类目录。新的任务从分类结构开始创建。

详细规划见 [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md)。

## 二、每个产品任务的标准结构

视频任务推荐：

```text
products/video/<task-slug>/
├── README.md
├── source/
├── generated/
├── metadata/
└── output/
    └── final.mp4
```

音乐任务推荐：

```text
products/music/<task-slug>/
├── README.md
├── source/
├── generated/
│   ├── lyrics.txt
│   └── style.txt
├── jobs/
│   └── current.json
├── review/
│   └── latest/
├── metadata/
├── docs/
└── output/
    └── final.wav
```

`review/latest/` 用于当前候选审核。正常自动化运行会把试听文件、请求、结果摘要和日志同步到这里，方便 ChatGPT 或后续 Codex 直接从 Git 检查一次运行。

`output/final.*` 只保存用户明确确认的最终版本。

## 三、音乐工作流

当前《后来没有故乡》任务位于：

```text
music-later-no-hometown-local-reproduction/
```

当前开发分支：

```text
feat/local-music-reproduction-v01
```

已完成：

```text
Apple Silicon / MLX 环境验证        PASS
ACE-Step 1.5 安装                   PASS
XL SFT 权重                         PASS
4B LM 权重                          PASS
本地 30 秒生成                      PASS
完整 Remix/Cover 路线              已验证可运行，但质量未达要求
REST API 自动化                     正在实施
```

后续正常工作方式：

```text
用户与 ChatGPT / Codex 讨论歌词和歌曲方向
    ↓
生成或更新 jobs/current.json
    ↓
用户当前阶段执行一条命令
    ↓
脚本启动或复用本地 ACE-Step REST API
    ↓
自动提交任务、等待、收集结果
    ↓
本地保留 WAV 候选
    ↓
生成轻量 review.mp3 + 请求 + 结果 + 日志
    ↓
自动提交并 push 到 Git 当前分支
    ↓
ChatGPT / Codex 从 Git 检查运行结果
    ↓
用户试听并给出结论
    ↓
继续调参或批准某个候选
```

完整自动化计划见当前音乐任务的 [`docs/API_AUTOMATION_PLAN.md`](music-later-no-hometown-local-reproduction/docs/API_AUTOMATION_PLAN.md)。

## 四、为什么审核阶段上传 MP3，最终阶段上传 WAV

完整 WAV 一首通常几十 MB。如果每次试验都把 WAV 放进 Git LFS，仓库历史会快速膨胀，而且已经上传的 LFS 对象无法通过普通删除立即回收远端空间。

因此当前约定：

```text
本地候选：candidate.wav，完整保留，直到该任务结束
Git 审核：review/latest/review.mp3，便于试听和模型检查
最终批准：output/final.wav，通过 Git LFS 保存
```

审核记录同时保存候选 WAV 的 SHA-256。最终批准时必须按 SHA-256 绑定到本机的准确候选，避免把别的生成结果误当成已批准版本。

## 五、Git LFS

大体积最终媒体通过 Git LFS 管理。当前 `.gitattributes` 已覆盖常用视频和音频格式。

推荐最终路径：

```text
视频：<task>/output/final.mp4
音乐：<task>/output/final.wav
```

审核用 MP3 可以直接进入 Git LFS 或普通 Git，具体取决于 `.gitattributes` 当前规则。

## 六、隐私与本机目录

以下内容默认不上传：

```text
模型权重
Hugging Face / ModelScope 缓存
ACE-Step 运行时
私有参考歌曲原文件
私有照片、视频、声音训练素材
临时 WAV、stem、repaint 片段
未选择的大量候选
密钥、cookie、token、.env
```

音乐运行时当前位于：

```text
/Users/jerson/AI/runtime/music/acestep-1.5
```

私有歌曲参考和运行候选放在 `~/AI/private/` 下。

## 七、自动化原则

自动化必须满足以下要求：

1. 任务参数进入结构化 JSON，减少 UI 隐含状态。
2. 每次运行生成唯一 run id。
3. 请求参数、模型版本、seed、输出 SHA-256 和日志必须可追踪。
4. 自动提交时只提交本次 review 路径，不能把本地其他脏文件一起提交。
5. 生成失败时也保留失败日志和请求摘要，便于定位。
6. 最终产品必须经过明确人工审核。
7. 清理临时产物只能发生在最终结果已经确认并远端验证之后。

后期 `codex-web-bridge` 稳定后，Codex 可以直接执行同一套脚本。音乐生成能力不需要耦合进 bridge 内部，bridge 只负责让 Codex 能稳定执行本机工具和继续任务。

## 八、当前兼容期说明

当前分支暂时保留旧的顶层任务目录，原因是本机工作区已有进行中的音乐生成和历史视频文件删除状态。此时直接移动目录会增加 Git 冲突风险。

兼容期策略：

```text
先建立新分类、脚本、运行契约
先把音乐 API 流程跑通
确认本地 worktree 干净
再做一次独立目录迁移提交
最后更新所有脚本相对路径
```

这样可以整理仓库，同时不打断正在进行的音乐实验和已有视频产物。