# AI 产物仓库

这个仓库用于保存经过 AI 工作流生成的可审阅产物、最终产物，以及复现这些产物所需要的轻量配置和日志。

它不是模型仓库，也不是私有素材仓库。模型权重、缓存、第三方参考音频、私有照片、训练数据、临时切片等大体量或敏感输入继续保存在本机私有目录。

## 仓库定位

本仓库长期承载多种 AI 产物，因此从 V0.4 开始按“产物类型”和“复用工作流”分开组织：

```text
ai_video_product/
├── README.md
├── .gitattributes
├── docs/                       仓库级规则、架构和审阅协议
├── products/                   真正的 AI 产物
│   ├── video/                  视频项目
│   ├── music/                  歌曲、配乐、音频项目
│   ├── image/                  图片项目
│   ├── document/               文档、报告等项目
│   └── other/                  暂时无法归类的其他产物
└── workflows/                  可复用的自动化脚本和模板
    ├── music/
    ├── video/
    └── shared/
```

`products/` 关注“做出了什么”，`workflows/` 关注“怎么自动做”。两者分开后，后续 Codex 可以复用同一套脚本生成很多首歌或很多个视频，不需要把自动化逻辑复制到每个项目里。

详细规则见 `docs/REPOSITORY_STRUCTURE.md`。

## 当前项目

### 音乐

```text
products/music/later-no-hometown/
```

用于《后来没有故乡》的本地生成、参考复现和 ACE-Step 自动化验证。

### 视频

```text
products/video/solana-university-video-1-something-i-shipped/
products/video/solana-university-video-2-something-i-organized/
```

原有视频项目保持内容不变，只调整到 `products/video/` 分类下。

## 音乐审阅流程

当前阶段采用“对话确定配置，用户执行命令，Git 作为审阅中转站”的方式：

```text
你和 ChatGPT 讨论歌词、风格和参数
        ↓
ChatGPT 更新本次 job 配置
        ↓
你在本机执行一条运行命令
        ↓
ACE-Step 本地生成
        ↓
脚本自动保存请求、日志、API 响应、技术元数据和试听 MP3
        ↓
脚本自动 commit + push 到 Git
        ↓
ChatGPT 从 Git 检查配置和日志
你直接试听 Git 中的 preview.mp3
        ↓
继续调参，或批准某个 run
        ↓
批准后再把本地无损/高质量结果提升为 output/final.wav
```

这样做的目的，是先把过程固定成可重复、可审计的命令行工作流。等 `codex-web-bridge` 可用后，把“你执行命令”这一环交给 Codex 即可，其余目录、job 格式、日志格式和审批逻辑都不需要推倒重来。

具体协议见：

```text
docs/RUN_REVIEW_PROTOCOL.md
workflows/music/ace-step/README.md
```

## 为什么普通候选只上传试听 MP3

每一轮都把 5 分钟以上的 WAV 上传到 Git LFS，会快速消耗 LFS 存储和带宽。普通候选因此采用：

```text
本地：保留原始生成 WAV
Git：上传 preview.mp3 + request.json + result.json + run.log + manifest.json
```

当你明确批准某个候选时，再把对应的本地 WAV 放入：

```text
products/<type>/<project>/output/final.*
```

这样既能在 Git 上审阅每一次生成，又能避免把大量失败 WAV 永久堆进 LFS。

如果某一轮确实需要保存原始 WAV，也可以在 job 配置中显式开启。

## 每个产物项目的推荐结构

```text
products/<type>/<project>/
├── README.md
├── source/             可以公开的输入说明或哈希，不放私有原素材
├── generated/          歌词、脚本、提示词等经确认的生成输入
├── config/             当前 job 和项目级配置
├── runs/               每次可审阅运行的记录
│   └── <run-id>/
│       ├── request.json
│       ├── release-response.json
│       ├── final-response.json
│       ├── run.log
│       ├── manifest.json
│       └── preview.mp3
├── output/             只放明确批准的最终产物
└── docs/               该项目特有的说明、进度和决策
```

视频项目可以使用 `final.mp4`，音乐项目可以使用 `final.wav` 或 `final.flac`，图片可以使用 `final.png` 等。

## Git LFS

仓库已经对常见视频和音频格式启用 Git LFS，包括：

```text
mp4 mov mkv wav flac m4a mp3 aac ogg
```

大型最终产物和审阅音频通过 LFS 保存。文本配置、日志、JSON、Markdown 仍使用普通 Git。

## 安全边界

默认禁止提交：

- 模型权重和模型缓存
- `.env`、Token、Cookie、私钥
- 未授权的第三方参考媒体
- 私有人声、照片、视频训练素材
- 大量临时渲染文件和失败中间产物
- 本机虚拟环境、依赖缓存

参考素材只在 Git 中保存安全的哈希、技术参数和复现说明。

## 当前开发分支

仓库分类和音乐命令化流程目前在：

```text
feat/product-layout-v04
```

完成本地验证后再决定合并回主分支。