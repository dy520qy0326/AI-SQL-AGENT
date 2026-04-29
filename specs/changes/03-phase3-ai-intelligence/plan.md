---
name: 03-phase3-ai-intelligence
title: Phase 3 — 技术实施方案
status: REVIEWED
created: 2026-04-29
---

## 架构影响分析

### 新增模块

```
backend/app/
├── ai/
│   ├── __init__.py
│   ├── client.py          # Claude API 封装（anthropic SDK）
│   ├── prompts.py         # Prompt 模板常量
│   ├── cache.py           # 语义缓存读写
│   └── service.py         # AI 服务编排（关系补全、注释补全）
├── nl/
│   ├── __init__.py
│   ├── context.py         # 上下文构造策略（token 裁剪）
│   └── router.py          # /ask 端点（SSE 流式 + 同步）
├── docgen/
│   ├── __init__.py
│   ├── generator.py       # Markdown 数据字典生成器
│   └── router.py          # 文档 CRUD 端点
├── api/
│   ├── ai.py              # AI Service API 路由
│   └── sessions.py        # 会话管理 API 路由
├── schemas/
│   ├── ai.py              # AI 请求/响应 Schema
│   ├── ask.py             # NL Query Schema
│   ├── session.py         # Session Schema
│   └── doc.py             # Doc Generation Schema
```

### 修改模块

| 文件 | 变更 |
|------|------|
| `app/db/models.py` | 新增 ConversationSession、ConversationMessage、AICache、GeneratedDoc 四个 ORM 模型 |
| `app/store/repository.py` | 新增 session CRUD、cache CRUD、doc CRUD 方法 |
| `app/config.py` | 新增 anthropic_api_key、ai_enabled、ai_model、ai_max_tokens 配置项 |
| `app/main.py` | 注册 ai_router、nl_router、sessions_router、docgen_router；lifespan 中 create_all 自动建新表 |
| `requirements.txt` | 新增 `anthropic>=0.40.0` |

### 与现有模块的关系

- `app/ai/` → 调用 `app/store/repository.py` 获取/写入表元数据和关系数据
- `app/ai/` → Anthropic SDK 调用 Claude API（同步调用，通过 `asyncio.to_thread` 适配异步）
- `app/nl/` → 调用 `app/store/` 获取 schema 上下文，调用 `app/ai/client.py` 发送聊天请求
- `app/docgen/` → 调用 `app/store/` 获取全量元数据，可选调用 `app/ai/` 做 AI 增强
- 不修改 `app/parser/`、`app/detector/`、`app/viz/` 模块

### 不涉及的部分

- 前端 React 项目（`src/`）— 不创建、不修改
- Phase 1 解析引擎 — 不变
- Phase 2 关系检测规则引擎 — 不变（AI 关系补全是新增链路，不修改现有规则）
- 版本对比 — Phase 4
- PDF/PlantUML 导出 — 后续提案

## 实现路径

### Task 1: AI 基础设施 + Claude API 封装

**目标**：安装 Anthropic SDK，实现 Claude API 调用封装和语义缓存。

- 依赖安装：`pipx inject fastapi anthropic`
- 扩展 `app/config.py`：`anthropic_api_key`、`ai_enabled`（默认 True）、`ai_model`（默认 `claude-sonnet-4-6`）、`ai_max_tokens`（默认 4096）
- 创建 `app/ai/client.py`：
  - `AIClient` 类封装 `anthropic.Anthropic`
  - `complete(prompt, system_prompt, max_tokens)` → AIResponse（同步，异步层使用 `asyncio.to_thread`）
  - 超时 30s，重试 1 次，失败抛出 `AIServiceError`
- 创建 `app/ai/prompts.py`：Prompt 模板常量（关系补全、注释补全、表说明生成、项目概览）
- 创建 `app/ai/cache.py`：
  - `get_cached(db, schema_hash, prompt_hash)` → cached JSON or None
  - `set_cache(db, schema_hash, prompt_hash, response_json, ttl_hours=24)`
  - `clear_cache(db)` — 清除全部缓存
  - `delete_expired(db)` — 清理过期缓存

**涉及文件**：
- `backend/app/config.py`（修改）
- `backend/app/ai/__init__.py`（新建）
- `backend/app/ai/client.py`（新建）
- `backend/app/ai/prompts.py`（新建）
- `backend/app/ai/cache.py`（新建）
- `backend/requirements.txt`（更新）

**验收**：API Key 未配置时返回明确错误；缓存命中/未命中逻辑正确

---

### Task 2: 数据模型扩展 + Repository 扩展

**目标**：新增 4 个 ORM 模型（Session、Message、AICache、GeneratedDoc）及对应 CRUD。

- `app/db/models.py` 新增：
  - `ConversationSession`（id, project_id FK, title, created_at, updated_at）
  - `ConversationMessage`（id, session_id FK, role enum(user/assistant), content text, sources JSON?, created_at）
  - `AICache`（id, cache_key str UNIQUE, prompt_hash, schema_hash, response JSON, created_at, expires_at）
  - `GeneratedDoc`（id, project_id FK, doc_type enum, title, content text, ai_enhanced bool, created_at）
- `app/store/repository.py` 新增：
  - `create_session(project_id)` → Session
  - `get_session(session_id)` → Session | None
  - `list_sessions(project_id)` → List[Session]
  - `delete_session(session_id)` → bool
  - `add_message(session_id, role, content, sources)` → Message
  - `get_messages(session_id, limit=20)` → List[Message]
  - `create_doc(project_id, ...)` → GeneratedDoc
  - `get_docs(project_id)` → List[GeneratedDoc]
  - `get_doc(doc_id)` → GeneratedDoc | None
  - `delete_doc(doc_id)` → bool
  - 以及 cache 读/写/清除方法

**涉及文件**：
- `backend/app/db/models.py`（修改）
- `backend/app/store/repository.py`（修改）

**验收**：新增模型建表成功；CRUD 方法单元测试通过；级联删除：删 Project → 级联删除关联 Sessions/Docs

---

### Task 3: AI Service — 关系补全与注释补全

**目标**：实现 `complete-relations` 和 `complete-comments` API。

- 创建 `app/ai/service.py`：
  - `complete_relations(project_id, db)`：
    1. 获取项目中无 Relation 的"孤立表"列表
    2. 构造 token 压缩的孤立表 JSON（仅表名 + PK + FK 列）
    3. 检查缓存 → 命中直接返回
    4. 调用 Claude API（relation_completion prompt）
    5. 解析 AI 返回的推荐关系
    6. 过滤 confidence=LOW 的 → 写入 Relation 表（INFERRED, source="AI suggested: {reason}"）
    7. 存储缓存
    8. 返回 {new_relations, ai_confidence_stats}
  - `complete_comments(project_id, db)`：
    1. 获取无注释的字段列表
    2. 调用 Claude API（comment_completion prompt）
    3. 更新 Column.comment（追加 "AI Generated" 标记）
    4. 返回 {updated_fields}
- 创建 `app/schemas/ai.py`
- 创建 `app/api/ai.py`：
  - `POST /api/projects/{id}/ai/complete-relations`
  - `POST /api/projects/{id}/ai/complete-comments`
  - `GET /api/projects/{id}/ai/status` — 返回 ai_enabled、cache_stats、last_completion
  - `POST /api/ai/cache/clear` — 清除缓存
- `app/main.py` 注册 ai_router

**并发控制**：使用 asyncio.Lock 按 project_id 串行化 AI 请求，同一项目并发请求返回 429。

**涉及文件**：
- `backend/app/ai/__init__.py`（修改）
- `backend/app/ai/service.py`（新建）
- `backend/app/schemas/ai.py`（新建）
- `backend/app/api/ai.py`（新建）
- `backend/app/main.py`（修改）

**验收**：AI 返回有效关系写入 DB；LOW 置信度关系不入库；相同 schema 二次请求命中缓存

---

### Task 4: NL Query — 上下文构造与问答

**目标**：实现自然语言问答，支持 SSE 流式和同步两种模式。

- 创建 `app/nl/context.py`：
  - `build_context(question, project_id, db)` → ContextPackage
  - 问题分析函数：提取关键词（表名、字段名）→ 定位候选表
  - 上下文裁剪策略按 Spec 规范实现：
    - 具体表查询 → 该表完整 schema
    - 跨表关系 → 涉及表 + 关系路径
    - 全局搜索 → 摘要模式
    - 模糊问题 → 完整摘要（max 30 表）
  - ContextPackage 包含：system_prompt（带 schema）、user_message、candidate_tables
- 创建 `app/schemas/ask.py`：AskRequest、AskSyncResponse（含 sources）、AskChunk
- 创建 `app/nl/router.py`：
  - `POST /api/projects/{id}/ask`（SSE）— 使用 `StreamingResponse`，`text/event-stream`
  - `POST /api/projects/{id}/ask/sync` — 标准 JSON 响应，含 sources
- 创建 `app/schemas/session.py`
- 创建 `app/api/sessions.py`：
  - `POST /api/sessions` — 创建会话
  - `GET /api/projects/{id}/sessions` — 项目会话列表
  - `GET /api/sessions/{id}/messages` — 会话消息历史
  - `DELETE /api/sessions/{id}` — 删除会话

**SSE 实现细节**：
- 使用 FastAPI `StreamingResponse` + async generator
- Claude API 调用时使用 `stream=True`，逐 token yield
- 对话消息在流结束后存储到 DB（含 sources）
- 错误时 yield `{"type": "error", "message": "..."}`

**涉及文件**：
- `backend/app/nl/__init__.py`（新建）
- `backend/app/nl/context.py`（新建）
- `backend/app/nl/router.py`（新建）
- `backend/app/schemas/ask.py`（新建）
- `backend/app/schemas/session.py`（新建）
- `backend/app/api/sessions.py`（新建）
- `backend/app/main.py`（修改）

**验收**：流式 SSE 正常推送；同步模式返回完整 JSON；上下文裁剪后 token 量符合预期

---

### Task 5: 文档生成

**目标**：实现 Markdown 数据字典生成，可选 AI 增强。

- 创建 `app/docgen/generator.py`：
  - `generate_markdown(project_id, db, ai_enhance=False)` → str
  - 纯模板模式（ai_enhance=False）：根据 Spec 模板填充表/字段/索引/关系数据
  - AI 增强模式（ai_enhance=True）：
    1. 先生成纯模板 Markdown
    2. 调用 AI 补全缺失的字段注释
    3. 调用 AI 生成表功能描述
    4. 调用 AI 生成项目数据模型概览
    5. 注入 Markdown 对应位置，标注 "AI Generated"
  - AI 增强为可选：每个 AI 步骤独立容错（一个失败不影响其他）
- 创建 `app/schemas/doc.py`
- 创建 `app/docgen/router.py`：
  - `POST /api/projects/{id}/docs` — 生成文档（body: `{ai_enhance: bool}`）
  - `GET /api/projects/{id}/docs` — 已生成文档列表
  - `GET /api/projects/{id}/docs/{doc_id}` — 获取文档内容（text/plain）
  - `DELETE /api/projects/{id}/docs/{doc_id}` — 删除文档

**涉及文件**：
- `backend/app/docgen/__init__.py`（新建）
- `backend/app/docgen/generator.py`（新建）
- `backend/app/docgen/router.py`（新建）
- `backend/app/schemas/doc.py`（新建）
- `backend/app/main.py`（修改）

**验收**：纯模板文档包含所有表/字段/索引/关系；AI 增强文档包含 AI 标注；容错正常

---

### Task 6: 集成测试与验证

**目标**：端到端测试，覆盖 AI 补全、NL Query、文档生成全链路。

- 准备测试 fixture：`backend/tests/fixtures/sample_ecommerce.sql`（10 张表，含孤立表）
- `backend/tests/test_ai_client.py`：client 单元测试（mock anthropic SDK）
- `backend/tests/test_ai_service.py`：关系补全 + 注释补全（mock AI 响应）
- `backend/tests/test_ai_cache.py`：缓存命中和过期逻辑
- `backend/tests/test_nl_context.py`：上下文构造策略测试（验证 token 裁剪）
- `backend/tests/test_nl_ask.py`：问答端点测试（SSE + sync，mock AI 响应）
- `backend/tests/test_sessions.py`：会话 CRUD 测试
- `backend/tests/test_docgen.py`：文档生成测试（模板 + AI 增强）

**测试场景清单**：
1. AI 关系补全：孤立表获得推荐关系 → 写入 DB
2. AI 关系补全：LOW 置信度不写入 DB
3. AI 缓存命中：二次相同请求返回 X-Cache: HIT
4. AI 禁用：规则引擎正常
5. NL Query SSE：流式推送逐 token 到达
6. NL Query 同步：返回完整 JSON + sources
7. 会话追问：上下文保持连贯
8. 文档生成：纯模板 → 完整性验证
9. 文档生成：AI 增强 → AI 内容标注验证
10. 并发控制：同一项目并发 AI 请求 → 429

**需要 mock 的对象**：
- `anthropic.Anthropic` — 所有测试中 mock AI 响应，避免依赖真实 API

**涉及文件**：
- `backend/tests/fixtures/sample_ecommerce.sql`（新建）
- `backend/tests/test_ai_client.py`（新建）
- `backend/tests/test_ai_service.py`（新建）
- `backend/tests/test_ai_cache.py`（新建）
- `backend/tests/test_nl_context.py`（新建）
- `backend/tests/test_nl_ask.py`（新建）
- `backend/tests/test_sessions.py`（新建）
- `backend/tests/test_docgen.py`（新建）

**验收**：所有测试通过；覆盖率 > 85%

---

## 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Claude API 延迟高（>10s） | NL Query 用户体验差 | SSE 流式响应减少感知延迟；超时 30s + 重试 1 次 |
| Anthropic SDK 同步调用阻塞事件循环 | FastAPI 吞吐下降 | 使用 `asyncio.to_thread` 将同步调用放入线程池 |
| AI 响应格式不稳定 | 解析失败导致功能不可用 | Prompt 中使用严格 JSON Schema 约束；解析失败时降级返回原始文本 |
| token 消耗过高 | API 成本不可控 | 上下文裁剪策略 + 语义缓存 + token 估算日志 |
| aiosqlite 并发限制 | 会话/缓存并发写入冲突 | SQLite 写锁串行化；高并发场景提示迁移 PostgreSQL |
| AI 幻觉（捏造不存在的字段/表） | 数据污染 | Prompt 明确要求仅引用已有字段；输出与 schema 做校验过滤 |
| 缺失 ANTHROPIC_API_KEY | 整个 AI 模块无法启动 | AI 禁用开关，规则引擎独立运行；返回 503 并明确提示配置 |

## 依赖安装

```bash
pipx inject fastapi anthropic
```

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| AI 调用方式 | `asyncio.to_thread` + 同步 Anthropic SDK | Anthropic Python SDK 无原生 async 支持；线程池适配避免阻塞事件循环 |
| 缓存存储 | SQLite（AICache 表）| 与已有基础设施一致，不引入 Redis 依赖；TTL 24h 数据量可控 |
| SSE 实现 | FastAPI `StreamingResponse` + async generator | 标准 SSE 协议，前端 EventSource 可直接消费 |
| AI 响应格式 | JSON（System Prompt 中约束 schema）| 结构化输出便于解析和校验；降低格式不稳定风险 |
| 上下文裁剪 | 关键词匹配 + 规则分类 | 不引入额外 NLP 依赖；轻量且可控 |

## 工作量估算

| Task | 估算 |
|------|------|
| Task 1: AI 基础设施 + Claude API 封装 | 中 |
| Task 2: 数据模型扩展 + Repository | 中 |
| Task 3: AI Service — 关系补全与注释补全 | 中 |
| Task 4: NL Query — 上下文构造与问答 | 大 |
| Task 5: 文档生成 | 中 |
| Task 6: 集成测试 | 中 |
