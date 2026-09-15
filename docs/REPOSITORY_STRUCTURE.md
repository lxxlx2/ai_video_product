# 仓库结构规划

## 目标

`ai_video_product` 作为 AI 产物仓库，需要同时支持视频、音乐和未来其他媒体类型，并且让 ChatGPT、Codex 和人工都能快速判断：

```text
这个任务是什么
输入是什么
运行过什么
当前候选是什么
最终批准的是哪个文件
哪些文件可以清理
```

仓库采用“产品任务”和“共享能力”分离的结构。

## 目标目录

```text
ai_video_product/
├── README.md
├── .gitattributes
├── docs/
│   ├── REPOSITORY_STRUCTURE.md
│   └── PRODUCT_WORKFLOW.md
├── products/
│   ├── video/
│   │   └── <task-slug>/
│   ├── music/
│   │   └── <task-slug>/
│   └── other/
│       └── <task-slug>/
├── shared/
│   ├── common/
│   ├── video/
│   └── music/
└── legacy-compatible-task-dirs/
```

## products

`products/` 中每个目录代表一个具体产物任务。

一个任务可以处于：

```text
draft      需求或参数仍在修改
running    正在生成
review     已有候选等待审核
approved   已明确批准一个候选
published  最终文件已经进入 Git 并完成远端验证
```

### 视频

```text
products/video/<task-slug>/
├── README.md
├── source/
├── generated/
├── metadata/
├── review/
└── output/
```

### 音乐

```text
products/music/<task-slug>/
├── README.md
├── source/
│   └── README.md
├── generated/
│   ├── lyrics.txt
│   └── style.txt
├── jobs/
│   ├── current.json
│   └── examples/
├── review/
│   └── latest/
│       ├── review.mp3
│       ├── request.json
│       ├── result.json
│       ├── run.json
│       ├── runner.log
│       └── server.log
├── metadata/
├── docs/
└── output/
    └── final.wav
```

`review/latest` 只代表最近一次需要人工判断的候选。历史由 Git commit 记录，不在工作树里无限堆 `candidate-001`、`candidate-002`。

完整 WAV 候选留在本机私有运行目录。Git 审核阶段上传压缩试听文件，并保存对应本地 WAV 的 SHA-256。

## shared

`shared/` 保存多个产品任务可复用的能力。

建议逐步形成：

```text
shared/music/
├── scripts/
│   ├── start_api.sh
│   ├── run_job.py
│   ├── publish_review.sh
│   └── finalize.sh
└── templates/
    ├── text2music.json
    └── cover.json
```

当前音乐自动化先在《后来没有故乡》任务目录内验证。验证通过后再抽到 `shared/music/`，避免过早抽象导致脚本在真实任务上不可用。

## 本机目录

Git 仓库只保留可公开、可复现、值得长期保留的文件。

运行时目录：

```text
~/AI/runtime/music/acestep-1.5
```

私有参考：

```text
~/AI/private/music-source/<task>/
```

本地运行结果：

```text
~/AI/private/music-runs/<task>/<run-id>/
```

单次运行目录推荐：

```text
<run-id>/
├── candidate.wav
├── request.json
├── response.json
├── run.json
├── runner.log
└── server.log
```

用户批准后，准确的 `candidate.wav` 才复制为 Git 中的 `output/final.wav`。

## 当前迁移策略

目前顶层存在：

```text
solana-university-video-1-something-i-shipped/
solana-university-video-2-something-i-organized/
music-later-no-hometown-local-reproduction/
```

计划最终迁移为：

```text
products/video/solana-university-video-1-something-i-shipped/
products/video/solana-university-video-2-something-i-organized/
products/music/later-no-hometown/
```

这次不立即移动，原因是本机工作树曾出现两个视频 `final.mp4` 的删除状态，同时音乐任务正在执行。直接移动会让 `git pull` 更容易产生冲突。

迁移触发条件：

```text
1. 当前音乐生成任务停止
2. review 自动化脚本至少成功跑一轮
3. 本机 git status 已确认
4. 现有删除状态已经明确保留或恢复
5. 单独提交一次 move-only 迁移
6. 迁移后更新脚本路径并回归验证
```

## 命名

任务 slug 使用稳定、可读的英文短名：

```text
later-no-hometown
solana-university-video-1-something-i-shipped
```

最终文件固定：

```text
output/final.mp4
output/final.wav
```

审核文件固定：

```text
review/latest/review.mp3
```

避免 `final-v2-final-new.wav` 一类文件名。版本由 Git commit 和 run id 表达。
