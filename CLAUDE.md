# AI SQL Agent — SDD 工作规范

## 项目概述

通过上传 SQL 文件（DDL 脚本），自动解析数据库表结构并识别表之间的关联关系（外键、索引、字段级引用等），借助 AI 能力提供可视化、智能问答和文档生成。

## SDD（Specification-Driven Development）

本项目遵循 **规范驱动开发** 范式。所有变更必须按四阶段工作流推进，阶段之间需人工确认后方可继续。

### 核心原则

1. **规范先行** — 编码前必须先完成规范定义，规范是人与 AI 之间的"契约"
2. **分阶段验证** — 每完成一个阶段必须暂停，等待人工 Review 后才能进入下一阶段
3. **规范即上下文** — 规范文档是唯一权威需求来源，AI 据此理解"做什么"和"为什么"

### 四阶段工作流

每一项变更必须依次经过以下四个阶段，**不可跳过任何阶段**：

```
Specify → Plan → Tasks → Implement
```

#### ① Specify（规范）
- 编写变更提案，定义业务规则、约束、成功标准
- 暂不涉及技术细节（语言、框架）
- 输出：`specs/changes/<name>/proposal.md`
- 标记为 `DRAFT`
- **等待人工 Review 确认 → 标记 REVIEWED 后方可进入下一阶段**

#### ② Plan（计划）
- 基于已确认的 Spec 拆解技术方案
- 包含：架构影响分析、实现路径、风险点、工作量估算
- 输出：`specs/changes/<name>/plan.md`
- **等待人工 Review 确认 → 标记 REVIEWED 后方可进入下一阶段**

#### ③ Tasks（任务分解）
- 将方案拆解为可执行的任务单元
- 每个任务包含：交付标准、验收条件、依赖关系
- 输出：`specs/changes/<name>/tasks.md`
- **等待人工 Review 确认 → 标记 REVIEWED 后方可进入下一阶段**

#### ④ Implement（实现）
- 按任务列表逐一编码实现
- 每完成一个任务暂停，等待 Review
- 原则：单次编码范围不超过 1 个 Task
- 编码后运行测试，确保不破坏现有功能
- 全部任务完成后：
  1. 更新 Spec 状态为 `ARCHIVED`
  2. 移至 `specs/archived/`
  3. 在 `specs/README.md` 中归档记录

### Spec 状态生命周期

```
DRAFT → REVIEWED → ACTIVE → ARCHIVED
```

| 状态 | 含义 |
|------|------|
| DRAFT | 起草中，尚未确认 |
| REVIEWED | 人工已确认，可进入下一阶段 |
| ACTIVE | 正在实现中 |
| ARCHIVED | 实现完成，已归档 |

## 角色定义

### Claude（协调者）
- 理解目标、拆分任务、决定实现路径
- 维护规范文档和项目上下文
- 在每个关键节点自问：
  - "当前处于哪个阶段？前置条件是否全部完成？"
  - "对应的 Spec 和 Task 是什么？"
- 每个阶段完成后总结进展，提出下一步建议，等待用户确认

## 决策框架

### 任何编码前必须自查
- [ ] 对应 Spec 是否存在且已获得 Review
- [ ] 技术方案是否已确认
- [ ] 当前要做的 Task 是否已明确交付标准

### 编码纪律
- 每次编码必须有明确的 Spec + Task 作为依据
- 单次编码范围限制在 1 个 Task 以内
- 不得一次性生成全部代码后提交
- 编码后运行相关测试验证

## 目录结构

```
specs/
  README.md            # Spec 索引
  changes/             # 活跃变更提案
    <name>/
      proposal.md      # 变更提案 (Specify 产出)
      plan.md          # 技术方案 (Plan 产出)
      tasks.md         # 任务分解 (Tasks 产出)
  archived/            # 已归档的变更记录
prd/                   # 原始 PRD（需求来源，保持不变）
```

## 开发环境

### 包管理

使用 `pipx` 替代 `pip` 管理 Python 依赖。所有项目依赖安装在 pipx 管理的 `fastapi` venv 中。

```bash
# 添加新依赖
pipx inject fastapi <package-name>

# 运行项目
pipx run --venv fastapi uvicorn app.main:app --port 8199

# 或直接使用 venv 的 Python
/home/ye/.local/share/pipx/venvs/fastapi/bin/python -m uvicorn app.main:app --port 8199
```

### 已安装依赖

- fastapi, sqlglot, pydantic-settings（注入到 fastapi venv）
- uvicorn（注入到 fastapi venv）

## 项目状态

- 技术栈：FastAPI (Python) + sqlglot + React + Claude API
- 当前阶段：Phase 1（核心解析引擎）— Task 1 完成
- 包管理：pipx（注入到 fastapi venv）
