# 仓库级文档索引

`docs/` 保存整个 `ai_video_product` 仓库的需求、设计和统一规范。

## 文档层级

### 1. 产品需求

[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)

定义：为什么做、解决什么问题、支持哪些产品、角色职责、标准生产生命周期、审核与批准规则、Git 与本地存储边界、自动化目标和验收标准。

需求发生变化时，优先更新该文档。

### 2. 技术设计

[`TECHNICAL_DESIGN.md`](TECHNICAL_DESIGN.md)

定义：系统架构、仓库和本机目录、Job / Run 数据模型、状态机、模型服务生命周期、Adapter、Orchestrator、Git 提交策略、Git LFS、Finalize、Cleanup、Codex 接管协议和技术实施顺序。

实现前先完成技术评审，代码和脚本需要符合该设计。

### 3. 仓库结构专项规范

[`REPOSITORY_STRUCTURE.md`](REPOSITORY_STRUCTURE.md)

聚焦 `products/`、`shared/`、`docs/`、具体产品目录结构、兼容期旧目录迁移和命名规范。

该文档是技术设计中仓库结构的专项展开。

### 4. 产品生产工作流

[`PRODUCT_WORKFLOW.md`](PRODUCT_WORKFLOW.md)

聚焦结构化配置、本地执行、候选生成、Git review、人工审核、最终固化和清理。

该文档是需求和技术设计中生命周期的操作规范。

## 文档优先级

出现冲突时按以下顺序处理：

```text
PRODUCT_REQUIREMENTS.md
        ↓
TECHNICAL_DESIGN.md
        ↓
REPOSITORY_STRUCTURE.md / PRODUCT_WORKFLOW.md
        ↓
具体产品目录中的 README / requirements / design
        ↓
脚本注释和临时记录
```

如果实现与上层文档不一致，需要先确认是实现问题还是需求变化，再决定修改代码或更新文档。

## 产品级文档

每个正式产品至少拥有：

```text
README.md
requirements.md
```

复杂项目增加：

```text
design.md
operations.md
progress.md
```

仓库级文档定义统一规则，产品级文档只记录该具体作品的需求、参数和特殊设计。

## 当前阶段

当前分支：`feat/local-music-reproduction-v01`

当前首个重点验证项目：《后来没有故乡》本地音乐生成与复现。

当前顺序：

```text
PRD 已评审通过
  ↓
技术设计 V0.1 已建立
  ↓
技术评审
  ↓
ACE-Step API READY 验证
  ↓
参考分析
  ↓
短片段参数实验
  ↓
完整歌曲
  ↓
Finalize / Cleanup
  ↓
抽取 shared/music
  ↓
仓库目录迁移
  ↓
Codex 接管
```
