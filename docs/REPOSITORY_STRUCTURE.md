# 仓库目录架构 V0.4

## 1. 目标

这个仓库长期保存多种 AI 产物，因此目录设计需要同时满足：

1. 一眼看出产物类型和项目归属；
2. 工作流脚本可以跨项目复用；
3. 每次生成都能留下可审计记录；
4. 最终产物和失败候选分开；
5. 未来 Codex 接管本地执行时无需重做仓库结构；
6. 私有素材、模型和缓存不进入公共 Git。

## 2. 顶层目录

```text
products/     AI 产物项目
workflows/    可复用自动化
 docs/        仓库级规范和协议
```

### products

按产物类型分目录：

```text
products/video/
products/music/
products/image/
products/document/
products/other/
```

新增项目时优先放进已有类型。只有确实无法分类时才进入 `other/`。

### workflows

这里保存“如何生成”的代码，不保存某一个作品的成品。

例如：

```text
workflows/music/ace-step/
workflows/video/
workflows/shared/
```

后续同一套 ACE-Step runner 可以服务所有歌曲项目。

## 3. 单个项目结构

推荐：

```text
products/<type>/<project>/
├── README.md
├── source/
├── generated/
├── config/
├── runs/
├── output/
├── metadata/
└── docs/
```

含义：

- `source/`：可公开的输入说明、URL、哈希和技术元数据。私有原媒体留在本机。
- `generated/`：当前确认的歌词、脚本、提示词、分镜等文本输入。
- `config/`：项目级配置和待执行 job。
- `runs/`：每次实际执行后的审阅记录。
- `output/`：明确批准的最终产物。
- `metadata/`：长期有价值的技术记录。
- `docs/`：项目特有的 runbook、进度、决策说明。

## 4. Run 是第一等对象

每次真正调用生成模型，都创建一个独立 run：

```text
runs/20260912-170501-r001/
├── request.json
├── release-response.json
├── final-response.json
├── run.log
├── manifest.json
├── ffprobe.json
└── preview.mp3
```

`run-id` 必须唯一并按时间可排序。

这样 ChatGPT 或 Codex 后续只需要读某个 run，就能知道：

- 当时用了什么模型；
- 提示词和歌词是什么；
- seed、时长、cover 参数是什么；
- API 是否成功；
- 实际生成文件 SHA-256；
- 用户试听的是哪一个文件；
- 该 run 是否被批准。

## 5. 候选与最终产物

候选运行默认上传压缩试听文件：

```text
runs/<run-id>/preview.mp3
```

高质量原始生成文件默认留本机工作区：

```text
.work/<type>/<project>/<run-id>/result.wav
```

批准以后，提升为：

```text
products/<type>/<project>/output/final.wav
```

最终文件必须记录来源 run-id 和 SHA-256。

## 6. Git LFS 策略

音视频二进制使用 Git LFS。普通文本使用普通 Git。

候选阶段上传 MP3 的原因是控制仓库增长。若每轮都保存 5 分钟 WAV，十几轮即可产生数 GB LFS 数据，而且 Git LFS 的历史对象仍会存在。

如果需要保留某轮无损候选，在 job 中显式设置：

```json
{
  "review": {
    "publish_full_audio": true
  }
}
```

默认值为 `false`。

## 7. 私有本机目录

模型、缓存、参考媒体继续放在仓库外：

```text
~/AI/runtime/                  模型运行时
~/AI/private/                  私有参考媒体
<repo>/.work/                  当前仓库临时工作文件，Git 忽略
```

`src_audio_path` 等路径允许在 job 中使用 `~`，runner 运行时展开。

## 8. 自动化边界

当前人工协作阶段：

```text
ChatGPT 修改配置
用户执行命令
脚本生成并 push run
ChatGPT 从 Git 检查日志
用户试听 preview
```

未来 Codex 阶段：

```text
ChatGPT/Codex 修改配置
Codex 执行相同命令
脚本生成并 push run
用户只负责试听和批准
```

因此当前脚本和 job schema 就是未来 Codex 的正式接口，不设计第二套自动化协议。

## 9. 迁移规则

V0.4 已把已有项目按类型归类：

```text
music-later-no-hometown-local-reproduction/
  -> products/music/later-no-hometown/

solana-university-video-1-something-i-shipped/
  -> products/video/solana-university-video-1-something-i-shipped/

solana-university-video-2-something-i-organized/
  -> products/video/solana-university-video-2-something-i-organized/
```

只调整路径，已有项目内容保留。

## 10. 命名规则

目录统一使用小写英文 slug，以便 shell、API 和自动化稳定使用。

推荐：

```text
later-no-hometown
solana-university-video-1-something-i-shipped
```

展示名称和中文标题写进项目 README 或 manifest，不使用中文目录名作为 Git 项目主路径。