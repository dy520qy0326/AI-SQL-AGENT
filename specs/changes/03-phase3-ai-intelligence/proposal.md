---
name: 03-phase3-ai-intelligence
title: Phase 3 — AI 智能增强
status: ACTIVE
created: 2026-04-29
---

## 摘要

在 Phase 2 元数据存储和关系检测的基础上，引入 Claude API 提供三项 AI 增强能力：AI 关系推断补全、自然语言查询（NL Query）、文档自动生成。使系统从"规则驱动"升级为"规则 + AI 混合引擎"。

## 动机

Phase 2 的规则引擎覆盖了约 85% 的关系检测场景（显式外键、`_id` 命名、同名字段），但仍有部分隐式关系无法被规则捕获（如语义关联、非标准命名、跨表业务耦合）。同时，用户上传 DDL 后希望能直接"对话"数据库结构，而不是通过 API 逐个查询表和字段。Phase 3 填补这一缺口：

- **AI Service** 封装 Claude API，提供关系补全和注释补全能力，补足规则引擎覆盖不到的 15%
- **NL Query** 支持自然语言问答，用户可像对话一样查询数据库结构，降低非技术用户的使用门槛
- **Doc Generation** 自动生成结构化 Markdown 数据字典，替代人工维护文档

## 范围

### 包含

**AI Service（P0）**
- Claude API 调用封装（含重试、超时、错误处理）
- 关系推断补全：将规则引擎未覆盖的表提交 AI，获得推荐关系 + 理由 + 置信度
- 字段注释补全：批量补全缺失注释的字段
- 表级描述生成：根据表结构和字段列表生成表功能说明
- 语义缓存：相同 schema 结构的 AI 响应命中缓存（cache_key = schema_hash + prompt_hash），TTL 24h
- AI 启用/禁用开关

**NL Query（P0-P1）**
- Schema 感知的上下文构造（按问题类型裁剪上下文，控制 token 消耗）
- 流式响应（SSE）：问题提交后逐字返回 AI 回答
- 同步响应：非流式选项
- 对话会话管理：创建/查看/删除会话，保持上下文连贯追问
- 关键词匹配：问题模糊时先定位候选表，再注入精确上下文
- 引用溯源：AI 回答中标注信息来源（表名、字段名）

**Doc Generation（P0-P1）**
- Markdown 数据字典：表总览 + 字段明细 + 索引清单 + 关系说明
- AI 增强：自动为缺失注释的字段生成说明、为表生成功能描述、为项目生成整体数据模型概览
- 可选的 AI 设计建议：分析 schema 给出索引优化和规范化建议
- 生成的文档可查询、可删除

### 不包含

- SQL 生成（"查询每个用户的订单总数" → 生成 SQL）— P2，后续提案
- 差异分析（"这个表和上一版本有什么不同"）— Phase 4
- PDF / PlantUML / Confluence 导出 — P2，后续提案
- 多轮对话中的模式推荐（"这种设计是否是星型模型"）— P2
- 前端 AI 对话 UI — Phase 3 仅提供后端 API
- 离线批量预测/模型 fine-tune
- 用户认证与配额管理

### 依赖

- PRD: `prd/05-ai-service.md`、`prd/06-nl-query.md`、`prd/07-doc-generation.md`
- 内部依赖：Phase 2 元数据存储 + 关系检测（`app/store/`、`app/detector/`）— 已完成
- 外部依赖：Claude API（通过 Anthropic SDK）
- 配置依赖：`ANTHROPIC_API_KEY` 环境变量

## 规范

### 数据模型

**ConversationSession**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| project_id | FK → Project | |
| title | str? | 会话标题（首条问题截取） |
| created_at | datetime | |
| updated_at | datetime | |

**ConversationMessage**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| session_id | FK → ConversationSession | |
| role | enum | user / assistant |
| content | text | 消息内容 |
| sources | JSON? | AI 回答的引用来源列表 |
| created_at | datetime | |

**AICache**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| cache_key | str UNIQUE | sha256(schema_hash + prompt_template + model) |
| prompt_hash | str | 提示词模板 hash |
| schema_hash | str | 项目 schema 结构 hash |
| response | JSON | 缓存的 AI 响应 |
| created_at | datetime | |
| expires_at | datetime | 过期时间（TTL 24h） |

**GeneratedDoc**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| project_id | FK → Project | |
| doc_type | enum | markdown / pdf / plantuml |
| title | str | 文档标题 |
| content | text | 文档内容（Markdown 源码） |
| ai_enhanced | bool | 是否启用 AI 增强 |
| created_at | datetime | |

### API 设计

**AI Service**
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/ai/complete-relations | AI 关系补全 |
| POST | /api/projects/{id}/ai/complete-comments | AI 注释补全 |
| GET | /api/projects/{id}/ai/status | AI 处理状态概览 |
| POST | /api/ai/cache/clear | 清除语义缓存 |

**NL Query**
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/ask | 提问（SSE 流式响应） |
| POST | /api/projects/{id}/ask/sync | 提问（非流式响应） |
| POST | /api/sessions | 创建会话 |
| GET | /api/sessions/{id}/messages | 获取会话消息历史 |
| DELETE | /api/sessions/{id} | 删除会话 |
| GET | /api/projects/{id}/sessions | 项目会话列表 |

**Doc Generation**
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/docs | 生成 Markdown 文档 |
| GET | /api/projects/{id}/docs | 已生成文档列表 |
| GET | /api/projects/{id}/docs/{doc_id} | 获取文档内容 |
| DELETE | /api/projects/{id}/docs/{doc_id} | 删除文档 |

### 上下文构造策略

为控制 Claude API token 消耗，按问题类型动态裁剪上下文：

| 问题模式 | 注入上下文 | token 估算 |
|---------|-----------|-----------|
| 具体表查询（"orders 表有哪些字段"） | 该表完整 schema + 关联关系 | ~500 tokens |
| 跨表关系（"用户和订单怎么关联"） | 涉及表 schema + 关系路径 | ~800 tokens |
| 全局搜索（"哪些表有 deleted_at"） | 所有表名 + 字段名摘要 | ~300 tokens |
| 模糊问题（"这个数据库做什么的"） | 完整项目 schema 摘要（max 30 表） | ~2000 tokens |
| 关系补全 | 未关联表 schema（token 压缩格式） | ~1500 tokens |
| 注释补全 | 无注释字段列表（table.column） | ~500 tokens |

### 成本控制

| 策略 | 规则 |
|------|------|
| 批处理 | 一次 AI 调用处理全部待补全内容，不逐表逐字段单独调用 |
| Token 压缩 | 关系补全仅传表名 + PK + FK 字段，不传全部字段类型细节 |
| 语义缓存 | 相同 schema hash + prompt template 命中缓存，24h TTL |
| 置信度过滤 | AI 自评 LOW 的推荐不写入 Relation 表，仅记录日志 |
| 并发限制 | 同一项目同时只允许 1 个 AI 请求（排队或返回 429） |
| 开关控制 | 可通过配置关闭 AI 功能，规则引擎独立运行 |

### 关系补全规则

1. 从项目获取所有未建立 Relation 的"孤立表"
2. 将孤立表列表 + 已有关联关系（供参考）提交 AI
3. AI 返回推荐关系列表（source_table, target_table, source_column, target_column, confidence, reason）
4. confidence 为 HIGH/MEDIUM 的写入 Relation 表（INFERRED, source="AI suggested: {reason}"）
5. confidence 为 LOW 的仅记录日志，不写入数据库
6. 已存在 Relation 的表对不重复推荐
7. 无合理关联线索时 AI 返回空列表（不捏造关系）

### NL Query 交互规范

- SSE 流式响应使用标准 `text/event-stream` 格式
- 每个 chunk 包含 `{"type": "chunk", "content": "..."}` 
- 流结束时发送 `{"type": "done"}`
- 错误时发送 `{"type": "error", "message": "..."}`
- 引用来源在最终消息的 `sources` 字段中返回
- 同一 session 内保留最近 20 轮对话作为上下文

### Doc Generation 格式规范

- Markdown 数据字典按：项目概览 → 表结构详情 → 关联关系 三段式组织
- AI 增强模式下，无注释字段标注 "AI Generated" 标记
- AI 表说明在表名下方以斜体引用格式展示
- 字段表格包含：序号、字段名、类型、NULL、PK、默认值、说明

### 错误处理

| 场景 | 行为 |
|------|------|
| Claude API 不可用 | 返回 503 + "AI 服务暂时不可用"，不影响规则引擎功能 |
| API Key 未配置 | 返回 503 + 明确提示配置 ANTHROPIC_API_KEY |
| API 超时（>30s） | 重试 1 次，仍失败返回 503 |
| 缓存命中 | 返回 200，响应头 X-Cache: HIT |
| 缓存未命中 | 调用 AI，存储缓存，返回 200，响应头 X-Cache: MISS |
| 同一项目并发 AI 请求 | 返回 429 + "请等待上一个 AI 请求完成" |
| 项目不存在 | 404 |
| 会话不存在 | 404 |
| 空问题 | 400 + "问题不能为空" |

## 验收标准

- [ ] AI 关系补全：对规则引擎未覆盖的表，AI 能发现合理关联并标注置信度
- [ ] AI 不自评 LOW 的关系不写入数据库
- [ ] 已有关联的表对不重复推荐
- [ ] 无关联线索时 AI 不捏造关系（返回空列表）
- [ ] 字段注释补全：生成的注释可读、无事实错误，标注 "AI Generated"
- [ ] NL Query 流式响应：首字到达 < 3s（SSE）
- [ ] 同一会话内上下文连贯：追问不丢失前文信息
- [ ] 关键词匹配准确率 > 95%（50 张表以上项目）
- [ ] AI 回答引用溯源：附带了正确的表名和字段名来源
- [ ] 文档生成包含所有表、字段、索引、关系，无遗漏
- [ ] AI 增强文档中表/字段说明无捏造（不引用不存在的字段名）
- [ ] 语义缓存：相同 schema + 相同 prompt 命中缓存，响应 < 500ms
- [ ] AI 禁用时规则引擎正常工作
- [ ] 单元测试覆盖率 > 85%

## 备注

- Phase 3 不包含前端 UI，仅提供后端 API
- AI 功能为可选增强，系统可在无 AI 配置下正常运行
- 语义缓存使用 SQLite 存储（与元数据共用 `backend/data/` 目录）
- Claude API 密钥通过 `ANTHROPIC_API_KEY` 环境变量配置
- 任意模块的 AI 增强均可独立开关
