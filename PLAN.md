# AI SQL Agent — 项目开发计划

## 1. 项目概述

通过上传 SQL 文件（DDL 脚本），自动解析数据库表结构并识别表之间的关联关系（外键、索引、字段级引用等），借助 AI 能力提供可视化、智能问答和文档生成。

## 2. 核心目标

| 目标 | 说明 |
|------|------|
| SQL 解析 | 支持 MySQL / PostgreSQL / SQLite DDL，提取表、字段、类型、约束 |
| 关系推理 | 显式外键 + 隐式关联（命名约定、字段类型匹配、AI 辅助推测） |
| 可视化 | 展示 ER 图 / 关系图谱（D3.js 或 Mermaid） |
| AI 问答 | 用户用自然语言查询表结构、字段含义、关联路径 |
| 导出集成 | 导出为 Markdown / PlantUML / 数据字典文档 |

## 3. 技术栈建议

| 层 | 技术选型 | 说明 |
|----|---------|------|
| 后端框架 | FastAPI (Python) 或 Node.js + Express | Python 生态 SQL 解析库丰富 |
| SQL 解析 | sqlparse + sqlglot（Python） | sqlglot 支持多种方言，容错性强 |
| AI SDK | anthropic（Claude API） | 处理模糊关系推断、自然语言查询 |
| 存储 | SQLite（开发）/ PostgreSQL（生产） | 存储解析后的元数据 |
| 前端 | React / Vue3 + D3.js / vis-network | 交互式关系图 |
| 可视化 | Mermaid.js（内嵌） | 快速嵌入文档导出 |
| 容器 | Docker + docker-compose | 一键启动 |

## 4. 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────────┐  │
│  │ SQL 上传  │ │ ER 图    │ │ AI 对话 / 查询       │  │
│  └────┬─────┘ └──────────┘ └─────────────────────┘  │
└───────┼─────────────────────────────────────────────┘
        │ REST / WebSocket
┌───────┼─────────────────────────────────────────────┐
│  ┌────┴─────────────────────────────────────────┐   │
│  │          API Layer (FastAPI)                  │   │
│  └────┬────────────────────────────────┬─────────┘   │
│       │                                │              │
│  ┌────┴────────┐           ┌───────────┴──────────┐  │
│  │ SQL Parser  │           │  AI Service (Claude) │   │
│  │ - sqlglot   │           │  - 关系补全推断      │   │
│  │ - 自定义AST │           │  - 自然语言查询      │   │
│  │ - 方言适配  │           │  - 文档自动生成      │   │
│  └────┬────────┘           └──────────────────────┘  │
│       │                                              │
│  ┌────┴─────────────────────────────────────────┐   │
│  │           Metadata Store (DB)                 │   │
│  │    tables / columns / indexes / relations     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 5. 数据模型设计

```yaml
Project:          # 项目（一次上传 = 一个项目）
  - id, name, description, created_at

Table:            # 解析得到的表
  - project_id, name, comment, engine (MySQL), schema_name

Column:           # 表的字段
  - table_id, name, type, nullable, default_value, primary_key, comment

Index:            # 索引
  - table_id, name, unique, columns (JSON)

Relation:         # 表间关系（显式 + 隐式）
  - source_table_id, source_column
  - target_table_id, target_column
  - relation_type: FOREIGN_KEY / INFERRED / AI_SUGGESTED
  - confidence: 0.0 ~ 1.0
```

## 6. 分阶段开发计划

### Phase 1：核心解析引擎 (2-3周)

- [ ] **工程初始化**
  - FastAPI 项目骨架，目录结构
  - SQLite 数据库 + SQLAlchemy ORM 模型
  - 基础异常处理和日志

- [ ] **SQL Parser 模块**
  - 实现 DDL 解析：CREATE TABLE（字段、类型、NOT NULL、DEFAULT、PRIMARY KEY）
  - 解析 UNIQUE、INDEX 定义
  - 解析 FOREIGN KEY（列级 + 表级约束）
  - 支持 MySQL 和 PostgreSQL 两种方言
  - 单元测试覆盖：标准 DDL、带注释 DDL、多表关联 DDL

- [ ] **Store 模块**
  - 将解析结果持久化到数据库
  - 上传 → 解析 → 存储 完整流水线
  - 上传 API endpoint: `POST /api/projects` + `POST /api/projects/{id}/upload`

- [ ] **关系可视化 API**
  - `GET /api/projects/{id}/tables` — 返回所有表及字段
  - `GET /api/projects/{id}/relations` — 返回表间关系数组
  - `GET /api/projects/{id}/graph` — 返回图数据结构（nodes + edges）

**Phase 1 验收标准：**
- 上传 MySQL DDL 文件 → 自动解析出 表/字段/主键/外键
- API 返回结构化数据，可在 Swagger 文档中验证
- 单元测试覆盖率 > 80%

### Phase 2：关系增强 + 可视化 (2周)

- [ ] **隐式关系推断**
  - 按命名约定推断：`order.user_id` → `user.id` 自动匹配
  - 按字段名 + 类型匹配（同名同类型字段建议为关联）
  - 置信度打分机制，低于阈值标记为 `INFERRED` 类型

- [ ] **基础前端界面**
  - 文件上传页（拖拽 + 点击上传）
  - 项目列表页
  - 项目详情页：表结构列表展示
  - ER 关系图（使用 vis-network 或 D3.js force layout）
  - 图中节点 = 表，边 = 外键/推断关系，颜色区分关系类型

- [ ] **Mermaid 导出**
  - 根据解析结果生成 Mermaid ER 图文本
  - 一键复制 / 下载

**Phase 2 验收标准：**
- 前端可上传 SQL 文件
- 浏览器中展示可交互的 ER 图
- 即使没有显式外键，也能推荐潜在关联

### Phase 3：AI 集成 (2周)

- [ ] **AI Service 模块**
  - 封装 Claude API 客户端
  - Prompt 模板：表结构上下文注入
  - 关系补全：AI 根据表名、字段名、注释推断遗漏的关系
  - 注释补全：AI 为无注释字段生成描述建议

- [ ] **自然语言查询**
  - `POST /api/projects/{id}/ask`
  - 将表结构转为结构化文本作为 context
  - 用户可以问："用户表和订单表怎么关联的？"、"哪个字段是支付金额？"
  - 流式响应（SSE）

- [ ] **文档自动生成**
  - `POST /api/projects/{id}/generate-doc`
  - AI 生成完整的数据字典文档（Markdown 格式）
  - 包含表说明、字段说明、关联说明

**Phase 3 验收标准：**
- AI 能补全典型的关系遗漏
- 自然语言查询准确率 > 85%
- 数据字典文档可直接用于团队分享

### Phase 4：增强功能 (2周)

- [ ] **多文件支持**
  - 一个项目可上传多个 SQL 文件
  - 跨文件关系解析

- [ ] **版本对比**
  - 同一个项目上传新版本 DDL
  - 差异对比 API：新增表、删除字段、变更类型
  - 前端高亮显示差异

- [ ] **团队协作**
  - 添加注释/备注到表和字段
  - 多人标注

- [ ] **导出能力增强**
  - PlantUML 导出
  - JSON Schema 导出
  - PDF 报告

## 7. AI 集成设计要点

### Prompt 模板策略

```
系统：你是一个数据库专家，以下是项目 {project_name} 的完整表结构：
{table_schemas_text}

用户问题：{user_question}

请基于表结构信息回答。如果信息不足，请明确指出。
```

### 关系补全 Prompt

```
分析以下数据库表结构，找出可能存在但未显式定义外键的关联关系。
对于每对候选关系，给出理由和置信度（高/中/低）。

表结构：
{json_schema}
```

### 缓存策略
- 每次项目更新后预热 AI context
- 相同问题使用语义缓存（减少 API 调用）

## 8. 项目目录结构

```
ai-sql-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── api/
│   │   │   ├── projects.py      # 项目相关路由
│   │   │   ├── tables.py        # 表相关路由
│   │   │   ├── relations.py     # 关系相关路由
│   │   │   └── ai.py            # AI 相关路由
│   │   ├── parser/
│   │   │   ├── base.py          # 解析器基类
│   │   │   ├── mysql.py         # MySQL DDL 解析
│   │   │   ├── postgres.py      # PostgreSQL DDL 解析
│   │   │   └── detector.py      # 隐式关系推断
│   │   ├── ai/
│   │   │   ├── client.py        # Claude API 客户端
│   │   │   ├── prompts.py       # Prompt 模板
│   │   │   └── schemas.py       # AI 输入输出 schema
│   │   ├── models/
│   │   │   └── db.py            # SQLAlchemy ORM 模型
│   │   └── schemas/
│   │       └── api.py           # Pydantic 请求/响应模型
│   ├── tests/
│   │   ├── test_parser.py
│   │   ├── test_detector.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.vue
│   │   │   ├── ProjectList.vue
│   │   │   ├── TableList.vue
│   │   │   ├── ErDiagram.vue
│   │   │   └── AiChat.vue
│   │   ├── api/
│   │   └── App.vue
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 9. 关键风险与应对

| 风险 | 应对 |
|------|------|
| SQL 方言差异导致解析错误 | 优先支持 MySQL/PostgreSQL，使用 sqlglot 做方言归一化 |
| 大型 DDL 文件（1000+ 表）解析慢 | 异步解析 + 进度回调，分批次处理 |
| AI API 延迟影响用户体验 | SSE 流式响应，前端做 loading 状态；离线场景支持纯规则推断 |
| 隐式关系误报太多 | 置信度分级，< 0.6 的关系默认折叠，需人工确认 |
| 用户数据安全（SQL 可能含敏感信息） | 纯本地部署选项，不上传外部；AI 调用可选本地模型 |

## 10. 实施建议

1. **先跑通核心链路**：Phase 1 做端到端 — 上传 → 解析 → 存库 → 返回 JSON。不急于做前端，先用 Swagger UI 验证。
2. **AI 是增强而非基础**：关系推断先用规则兜底，AI 作为补充。确保去掉 AI 核心功能仍可用。
3. **测试先行**：SQL 解析引擎准备好一批评测 DDL 样本（MySQL 官方 sample + 真实业务脱敏 DDL），集成到 CI。
4. **TDD for Parser**：SQL 解析逻辑复杂，先写测试用例再实现。
