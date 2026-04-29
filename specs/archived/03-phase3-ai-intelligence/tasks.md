---
name: 03-phase3-ai-intelligence
title: Phase 3 — 任务分解
status: REVIEWED
created: 2026-04-29
---

## 依赖关系

```
Task 1 (AI 基础设施) ──→ Task 2 (数据模型) ──→ Task 3 (AI Service)
                                                    │
                                                    ├──→ Task 4 (NL Query) ──→ Task 6 (集成测试)
                                                    │
                                                    └──→ Task 5 (文档生成) ──┘
```

Task 3 是核心链路瓶颈。Task 4 和 Task 5 在 Task 3 完成后可并行。

---

## Task 1: AI 基础设施 + Claude API 封装

**依赖**：无（Phase 2 已完成）

**交付标准**：
- [ ] 依赖安装：`pipx inject fastapi anthropic`
- [ ] `app/config.py` 扩展：
  - `anthropic_api_key: str = ""`
  - `ai_enabled: bool = True`
  - `ai_model: str = "claude-sonnet-4-6"`
  - `ai_max_tokens: int = 4096`
- [ ] `app/ai/client.py`：
  - `AIServiceError` 异常类
  - `AIClient` 类封装 `anthropic.Anthropic`
  - `complete(system_prompt, user_message, max_tokens, temperature=0.3)` → str
  - `complete_stream(system_prompt, user_message, max_tokens)` → Iterator[str]（流式）
  - 超时 30s，重试 1 次，失败抛出 `AIServiceError`
  - `ai_enabled=False` 时抛出 `AIServiceError("AI service is disabled")`
  - `ANTHROPIC_API_KEY` 为空时抛出 `AIServiceError("ANTHROPIC_API_KEY not configured")`
- [ ] `app/ai/prompts.py`：Prompt 模板常量
  - `RELATION_COMPLETION_SYSTEM`
  - `RELATION_COMPLETION_USER`（含 JSON schema 输出约束）
  - `COMMENT_COMPLETION_SYSTEM`
  - `COMMENT_COMPLETION_USER`
  - `TABLE_DESCRIPTION_SYSTEM`
  - `TABLE_DESCRIPTION_USER`
  - `PROJECT_SUMMARY_SYSTEM`
  - `PROJECT_SUMMARY_USER`
  - `NL_QUERY_SYSTEM`
- [ ] `app/ai/cache.py`：
  - `make_cache_key(schema_hash, prompt_hash)` → str
  - `get_cached(db, cache_key)` → dict | None
  - `set_cache(db, cache_key, prompt_hash, schema_hash, response, ttl_hours=24)`
  - `clear_all(db)` — 清除所有过期和非过期缓存
  - 从 AICache 表读写

**涉及文件**：
- `backend/app/config.py`（修改）
- `backend/app/ai/__init__.py`（新建）
- `backend/app/ai/client.py`（新建）
- `backend/app/ai/prompts.py`（新建）
- `backend/app/ai/cache.py`（新建）

**验收**：
1. `ai_enabled=False` 时 client 抛出 AIServiceError
2. 无 API Key 时抛出明确错误提示
3. 缓存读写正确，过期缓存不会被命中

---

## Task 2: 数据模型扩展 + Repository 扩展

**依赖**：Task 1（需要 `app/db/models.py` 中的 AICache 模型由 Task 2 创建，但 cache.py 需要模型定义 → 实际 Task 2 需在 cache.py 之前建立 AICache 模型框架）

**交付标准**：
- [ ] `app/db/models.py` 新增 4 个 ORM 模型：
  - `ConversationSession`
    - id: String(36) PK, default uuid
    - project_id: FK → projects.id, ondelete CASCADE
    - title: String(500), nullable
    - created_at: DateTime, default utcnow
    - updated_at: DateTime, default utcnow, onupdate utcnow
    - messages → relationship("ConversationMessage", cascade delete-orphan)
  - `ConversationMessage`
    - id: String(36) PK, default uuid
    - session_id: FK → conversation_sessions.id, ondelete CASCADE
    - role: String(20) — "user" / "assistant"
    - content: Text
    - sources: JSON, nullable（AI 引用来源列表）
    - created_at: DateTime, default utcnow
  - `AICache`
    - id: String(36) PK, default uuid
    - cache_key: String(128), UNIQUE, index
    - prompt_hash: String(64)
    - schema_hash: String(64)
    - response: JSON
    - created_at: DateTime, default utcnow
    - expires_at: DateTime
  - `GeneratedDoc`
    - id: String(36) PK, default uuid
    - project_id: FK → projects.id, ondelete CASCADE
    - doc_type: String(20) — "markdown" / "pdf" / "plantuml"
    - title: String(500)
    - content: Text
    - ai_enhanced: Boolean, default False
    - created_at: DateTime, default utcnow
- [ ] `app/db/models.py` 中 Project 添加 relationships：
  - sessions → relationship("ConversationSession")
  - docs → relationship("GeneratedDoc")
- [ ] `app/store/repository.py` 新增方法：
  - **Session**
    - `create_session(project_id, title=None)` → ConversationSession
    - `get_session(session_id)` → ConversationSession | None
    - `list_project_sessions(project_id)` → List[ConversationSession]（按 updated_at 降序）
    - `delete_session(session_id)` → bool
  - **Message**
    - `add_message(session_id, role, content, sources=None)` → ConversationMessage
    - `get_messages(session_id, limit=20)` → List[ConversationMessage]（按 created_at 升序）
  - **Cache**
    - `get_cached(cache_key)` → dict | None（检查 expires_at > now）
    - `set_cache(cache_key, prompt_hash, schema_hash, response, ttl_hours=24)` → AICache
    - `clear_all_cache()` → int（删除数量）
    - `delete_expired_cache()` → int
  - **Doc**
    - `create_doc(project_id, doc_type, title, content, ai_enhanced)` → GeneratedDoc
    - `list_docs(project_id)` → List[GeneratedDoc]（按 created_at 降序）
    - `get_doc(doc_id)` → GeneratedDoc | None
    - `delete_doc(doc_id)` → bool

**注意**：Task 1 的 `app/ai/cache.py` 通过 Repository 方法读写缓存，不直接操作 ORM。

**涉及文件**：
- `backend/app/db/models.py`（修改）
- `backend/app/store/repository.py`（修改）

**验收**：
1. 启动应用后 4 张新表自动创建
2. Session CRUD 单元测试通过（含级联删除）
3. Cache 过期逻辑正确（expires_at < now 的记录不被 get_cached 返回）
4. Doc CRUD 单元测试通过

---

## Task 3: AI Service — 关系补全与注释补全

**依赖**：Task 1, Task 2

**交付标准**：
- [ ] `app/ai/service.py`：
  - `compute_schema_hash(project_id, db)` → str（对表名+字段名列表做 sha256）
  - `compute_prompt_hash(prompt_template)` → str（sha256）
  - `complete_relations(project_id, db)` → dict：
    1. 从 Repository 获取项目中没有任何 Relation 的"孤立表"
    2. 若孤立表 ≤ 1 张 → 返回 `{"new_relations": [], "message": "no isolated tables"}`
    3. 构造 token 压缩 JSON（仅表名 + PK 列 + `_id` 后缀列）
    4. 计算 schema_hash + prompt_hash → 查缓存
    5. 缓存命中 → 解析缓存响应为 RelationData 列表 → 写入 DB → 返回
    6. 缓存未命中 → 调用 `client.complete()` → 解析响应
    7. 解析后校验：过滤掉引用了不存在表/字段的关系
    8. 按 confidence 过滤：HIGH/MEDIUM → 写入 INFERRED Relation（source="AI suggested: {reason}"）；LOW → 仅记录日志
    9. 存储缓存 → 返回结果
  - `complete_comments(project_id, db)` → dict：
    1. 获取项目中所有 comment=NULL 的字段
    2. 若无 → 返回 `{"updated": 0, "message": "no missing comments"}`
    3. 查缓存 → 命中则直接更新 Column.comment（追加 " [AI Generated]"）
    4. 未命中 → 调用 AI → 解析 → 更新 Column.comment
    5. 返回 `{"updated": N, "fields": [...]}`
  - `generate_table_descriptions(project_id, db)` → dict：
    1. 对每张无 comment 的表调用 AI 生成表描述
    2. 更新 Table.comment（追加 " [AI Generated]"）
  - `generate_project_summary(project_id, db)` → str：
    1. 获取项目所有表摘要 → AI 生成整体数据模型概览

- [ ] `app/schemas/ai.py`：
  - `AICompleteRelationsResponse(new_relations_count, relations, cache_hit, message)`
  - `AICompleteCommentsResponse(updated_count, fields, cache_hit, message)`
  - `AIStatusResponse(ai_enabled, ai_model, cache_count, last_completion)`

- [ ] `app/api/ai.py`：
  - `POST /api/projects/{project_id}/ai/complete-relations` → 200 / 404 / 503
  - `POST /api/projects/{project_id}/ai/complete-comments` → 200 / 404 / 503
  - `GET /api/projects/{project_id}/ai/status` → 200 / 404
  - `POST /api/ai/cache/clear` → 200

**并发控制**：字典 `_locks: dict[str, asyncio.Lock]` 按 project_id 加锁，同一项目并发 AI 请求 → 后到达的返回 409 "AI request already in progress for this project"

**涉及文件**：
- `backend/app/ai/__init__.py`（修改 — 暴露 service 函数）
- `backend/app/ai/service.py`（新建）
- `backend/app/schemas/ai.py`（新建）
- `backend/app/api/ai.py`（新建）
- `backend/app/main.py`（修改 — 注册 ai_router）

**验收**：
1. 孤立表获得 AI 推荐关系 → 写入 Relation 表（INFERRED, AI suggested）
2. LOW 置信度关系不写入 DB
3. 已存在 Relation 的表不包含在孤立表中
4. 缓存命中时响应头含 X-Cache: HIT
5. 无孤立表时返回空列表 + 说明
6. 注释补全后 Column.comment 含 "AI Generated" 标记
7. 同一项目并发请求 → 409

---

## Task 4: NL Query — 上下文构造与问答

**依赖**：Task 2, Task 3（需要 session 存储和 AI client）

**交付标准**：
- [ ] `app/nl/context.py`：
  - `ContextPackage` dataclass：system_prompt, user_message, candidate_tables, token_estimate
  - `build_context(db, project_id, question, session_id=None)` → ContextPackage
  - 上下文裁剪规则：
    1. 问题中提取表名关键词（所有项目表名在问题中做子串匹配）
    2. 同时提取字段名关键词（所有字段名在问题中做子串匹配）
    3. 匹配到的表数 = 0 → 模糊模式：全部表摘要（max 30），token_estimate = 表数 × 50
    4. 匹配到的表数 = 1 → 单表模式：该表完整 schema + 其 Relation 关联表名，token_estimate = 500
    5. 匹配到的表数 2-3 → 关系模式：涉及表完整 schema + Relation 详情，token_estimate = 800
    6. 匹配到的表数 > 3 或仅字段名匹配 → 搜索模式：所有表名+字段名摘要，token_estimate = 300
  - `schema_to_context_text(tables, relations=None, mode="full")` → str
    - full 模式：每表展示所有字段（名称+类型+PK/FK标记+注释）
    - summary 模式：每表仅展示表名 + PK + 关联字段
  - `extract_table_keywords(question, table_names)` → list[str]
  - `extract_column_keywords(question, column_names_by_table)` → list[str]
  - 对话历史注入：session_id 非空时，获取最近消息拼接到 user_message 中

- [ ] `app/nl/router.py`：
  - `POST /api/projects/{project_id}/ask`（SSE 流式）：
    - 创建/复用 session（首次自动创建）
    - 调用 `build_context()` 构造上下文
    - 调用 `client.complete_stream()` 获取流式响应
    - `StreamingResponse` + async generator yield SSE chunk
    - 流结束后存储 user message + assistant message 到 DB（含 sources）
    - 自动更新 session 标题（取首条 user 问题前 50 字符）
  - `POST /api/projects/{project_id}/ask/sync`（非流式）：
    - 同上流程，但使用 `client.complete()` 返回完整 JSON
    - 响应体含 answer + sources
  - SSE chunk 格式：
    ```
    data: {"type": "chunk", "content": "..."}\n\n
    data: {"type": "done"}\n\n
    data: {"type": "error", "message": "..."}\n\n
    ```
  - sources 提取：从 AI 回答中解析引用标记 `[表名.字段名]` 或在 system prompt 中要求 AI 在末尾单独列出 sources JSON

- [ ] `app/schemas/ask.py`：
  - `AskRequest(question, session_id=None)` — session_id 为空时自动创建
  - `AskSyncResponse(answer, sources, session_id)`
  - `AskSource(table_name, column_name?, description)`

- [ ] `app/api/sessions.py`：
  - `POST /api/sessions` — 创建会话（body: `{project_id, title?}`）
  - `GET /api/projects/{project_id}/sessions` — 项目会话列表
  - `GET /api/sessions/{session_id}/messages` — 会话消息历史
  - `DELETE /api/sessions/{session_id}` — 删除会话

- [ ] `app/schemas/session.py`：
  - `SessionCreate(project_id, title?)`
  - `SessionResponse(id, project_id, title, created_at, updated_at, message_count)`
  - `MessageResponse(id, session_id, role, content, sources, created_at)`

- [ ] `app/main.py` 注册 nl_router 和 sessions_router

**涉及文件**：
- `backend/app/nl/__init__.py`（新建）
- `backend/app/nl/context.py`（新建）
- `backend/app/nl/router.py`（新建）
- `backend/app/schemas/ask.py`（新建）
- `backend/app/schemas/session.py`（新建）
- `backend/app/api/sessions.py`（新建）
- `backend/app/main.py`（修改）

**验收**：
1. SSE 流式推送：curl 可观察到逐 chunk 输出
2. 同步模式返回完整 JSON + sources
3. 同一会话内追问：上下文含前文消息
4. 上下文裁剪：单表问题只注入该表 schema（验证 token 量级）
5. 全局搜索：匹配到所有相关表
6. 会话删除：消息级联清除

---

## Task 5: 文档生成

**依赖**：Task 2, Task 3（需要 AI client 做增强）

**交付标准**：
- [ ] `app/docgen/generator.py`：
  - `generate_markdown(project_id, db, ai_enhance=False)` → str
  - 模板结构（按 Spec 规范）：
    ```
    # 数据字典 - {project_name}
    > 生成时间: {now} | 表总数: {N} | 关系总数: {M}

    ## 一、项目概览
    {ai_summary or "（无描述）"}

    ## 二、表结构详情
    ### 2.N {table_name} (`{schema}.{table_name}`)
    {ai_table_description or comment}
    | # | 字段名 | 类型 | NULL | PK | 默认值 | 说明 |
    ...
    **索引：** ...
    **外键：** ...

    ## 三、关联关系
    | 来源表 | 来源字段 | 目标表 | 目标字段 | 类型 | 置信度 | 来源 |
    ```
  - 纯模板模式（ai_enhance=False）：直接填充元数据
  - AI 增强模式（ai_enhance=True）：
    1. 调用 `generate_project_summary()` → 插入项目概览
    2. 对每张表调用 `generate_table_descriptions()` → 插入表描述
    3. 对缺失注释的字段调用 `complete_comments()` → 填入说明列
    4. AI 生成内容标注 " [AI Generated]"
    5. 每个 AI 步骤独立 try/except，单个失败不中断整体生成
  - `extract_or_generate_ai_summary(doc_id, db)` → 从 GeneratedDoc 提取 AI 概览文本

- [ ] `app/docgen/router.py`：
  - `POST /api/projects/{project_id}/docs`（body: `{ai_enhance: bool, title?}`）→ 201
  - `GET /api/projects/{project_id}/docs` → 文档列表
  - `GET /api/projects/{project_id}/docs/{doc_id}` → 返回 Markdown 文本（`PlainTextResponse`，`text/markdown`）
  - `DELETE /api/projects/{project_id}/docs/{doc_id}` → 204

- [ ] `app/schemas/doc.py`：
  - `DocGenerateRequest(ai_enhance=True, title=None)`
  - `DocResponse(id, project_id, doc_type, title, ai_enhanced, created_at, content_snippet)` — content_snippet 为前 200 字符
  - `DocListResponse(items, total)`

- [ ] `app/main.py` 注册 docgen_router

**涉及文件**：
- `backend/app/docgen/__init__.py`（新建）
- `backend/app/docgen/generator.py`（新建）
- `backend/app/docgen/router.py`（新建）
- `backend/app/schemas/doc.py`（新建）
- `backend/app/main.py`（修改）

**验收**：
1. 纯模板文档：所有表/字段/索引/关系完整呈现
2. AI 增强文档：含 AI 标注的字段注释和表描述
3. AI 部分失败时文档仍可生成（容错）
4. 文档 CRUD 正确（创建→查询→删除）
5. 文档内容为有效 Markdown（GitHub 风格）

---

## Task 6: 集成测试与验证

**依赖**：Task 1-5 全部完成

**交付标准**：
- [ ] `backend/tests/fixtures/sample_ecommerce.sql`：10 张表电商场景 DDL
  - 包含：用户/订单/商品/分类/购物车/评论/地址/支付/库存/物流
  - 5 张表有显式 FK，2 张表用 `_id` 命名无显式 FK，3 张表完全独立（孤立表）
  - 部分字段无 comment

- [ ] `backend/tests/test_ai_client.py`：
  - mock `anthropic.Anthropic` → 测试 `AIClient.complete()`
  - 测试 `ai_enabled=False` → AIServiceError
  - 测试 API Key 为空 → AIServiceError
  - 测试 API 返回 → 解析正确
  - 测试 API 超时 → 重试逻辑
  - 测试流式 `complete_stream()` → 逐 chunk yield

- [ ] `backend/tests/test_ai_cache.py`：
  - 测试缓存写入 → 命中 → 过期
  - 测试 clear_all → 缓存清空
  - 测试 schema_hash 变化 → 新缓存 key

- [ ] `backend/tests/test_ai_service.py`（mock AI client）：
  - 测试关系补全：孤立表 → 获得推荐 → 写入 DB
  - 测试 LOW 置信度过滤
  - 测试已有关联表不重复
  - 测试无孤立表 → 返回空
  - 测试注释补全：无注释字段 → 更新 comment
  - 测试并发控制：同一 project 并发 → 409

- [ ] `backend/tests/test_nl_context.py`：
  - 测试单表关键词匹配 → 单表模式上下文
  - 测试跨表关键词 → 关系模式上下文
  - 测试无匹配关键词 → 模糊模式（摘要）
  - 测试上下文 token 量估算
  - 测试对话历史注入

- [ ] `backend/tests/test_nl_ask.py`（mock AI client）：
  - 测试 SSE 流式响应 → chunk 格式正确
  - 测试同步响应 → JSON 完整
  - 测试会话自动创建
  - 测试追问上下文连贯
  - 测试空问题 → 400

- [ ] `backend/tests/test_sessions.py`：
  - 测试会话 CRUD 全链路
  - 测试消息存储和查询
  - 测试级联删除

- [ ] `backend/tests/test_docgen.py`：
  - 测试纯模板生成 → 内容完整性
  - 测试 AI 增强生成 → AI 标注
  - 测试 AI 部分失败容错
  - 测试 Doc CRUD

**涉及文件**：
- `backend/tests/fixtures/sample_ecommerce.sql`（新建）
- `backend/tests/test_ai_client.py`（新建）
- `backend/tests/test_ai_cache.py`（新建）
- `backend/tests/test_ai_service.py`（新建）
- `backend/tests/test_nl_context.py`（新建）
- `backend/tests/test_nl_ask.py`（新建）
- `backend/tests/test_sessions.py`（新建）
- `backend/tests/test_docgen.py`（新建）

**验收**：
- [ ] `pytest` 全量通过（含已有 294 个测试 + 新增测试）
- [ ] 覆盖率 > 85%（`pytest --cov=app --cov-report=term`）
- [ ] 无真实 Claude API 调用（全部 mock）

---

## 执行顺序总结

```
Task 1 ──→ Task 2 ──→ Task 3 ──→ Task 4 ──→ Task 6
                              ↘─→ Task 5 ──↗
                               (Task 4/5 可部分并行)
```

每完成一个 Task 暂停，等待 Review 后再继续下一个。
