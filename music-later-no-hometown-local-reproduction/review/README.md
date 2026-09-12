# 审核快照

`latest/` 由自动化脚本维护，用于保存最近一次需要人工审核的轻量结果。

正常成功运行后包含：

```text
latest/
├── review.mp3
├── request.json
├── result.json
├── run.json
├── runner.log
└── server.log
```

完整 WAV 候选保留在本机 `~/AI/private/music-runs/later-no-hometown/<run-id>/`。

`run.json` 保存完整候选的本地路径和 SHA-256。用户批准时以 SHA-256 为准，再把准确候选提升为 `output/final.wav`。

`latest/` 每次运行覆盖当前工作树中的旧审核快照，历史通过 Git commit 保留。