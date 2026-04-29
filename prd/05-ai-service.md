# PRD: AI Service 模块

## 1. 产品概述

AI Service 模块封装 Claude API，为系统提供三项核心 AI 能力：关系推断补全、字段注释补全、数据字典生成。它是系统的"智能增强层"，在规则引擎覆盖不到的场景发挥作用。

## 2. 目标用户

- **直接用户**：通过 API 调用的后端模块（Relation Detector、文档生成器）
- **间接用户**：通过前端交互使用 AI 功能的最终用户

## 3. 功能需求

### P0 — 关系补全

| 功能 | 说明 |
|------|------|
| 剩余表关系分析 | 将规则引擎无法关联的表提交 AI，分析潜在关系 |
| 推荐关系输出 | AI 给出推荐关联 + 字段级理由 |
| 置信度标注 | AI 同时给出理由和自评置信度 |

### P1 — 字段注释补全

| 功能 | 说明 |
|------|------|
| 缺失注释批量补全 | 对 comment 为空的字段，先按表 + 字段名批量生成 |
| 表说明生成 | 根据表名 + 字段列表生成表级描述 |
| 争议标注 | 低置信度的补全标注 "AI Generated"，供人工审核 |

### P2 — AI 对话增强

| 功能 | 说明 |
|------|------|
| Schema Context 注入 | 将完整表结构转为 token 优化的文本，作为对话背景 |
| 追问澄清 | 当用户问题模糊时，AI 主动反问以明确意图 |

## 4. Prompt 设计

### 关系补全 Prompt

```
你是一个数据库专家。以下是一个项目的数据库表结构（JSON 格式），
其中部分表之间尚未建立关联关系。请分析这些表，找出可能的关联。

分析要求：
1. 只建议有合理依据的关系（字段名匹配、语义匹配、主外键模式）
2. 对每个推荐给出具体理由
3. 标注置信度：HIGH / MEDIUM / LOW
4. 返回 JSON 格式

未关联表：{unlinked_tables_json}
已有关联（供参考）：{existing_relations_json}

返回格式：
[
  {
    "source_table": "...",
    "target_table": "...",
    "source_column": "...",
    "target_column": "...",
    "confidence": "HIGH|MEDIUM|LOW",
    "reason": "..."
  }
]
```

### 注释补全 Prompt

```
根据表名、表注释（如有）和字段名，为以下无注释的字段生成中文注释建议。
每个建议一行，格式： table.column → 建议注释

{context}

返回 JSON:
{"suggestions": [{"table": "...", "column": "...", "comment": "..."}]}
```

## 5. 成本控制策略

| 策略 | 说明 |
|------|------|
| 批处理调用 | 一次调用将整个项目未关联表送 AI，减少 API 次数 |
| token 压缩 | 仅传表名 + 主键 + 外键字段，不传全部字段类型 |
| 语义缓存 | 相同 schema 结构的问题命中缓存（key = schema hash + prompt hash） |
| 置信度阈值 | AI 自评 LOW 的关系不写入数据库，仅记录日志 |
| 可选开关 | 用户可选择关闭 AI 功能，仅使用规则引擎 |

## 6. 缓存设计

```
cache_key = sha256(schema_hash + prompt_template + model)
cache_ttl = 24h（schema 不变的情况下）
存储: Redis 或本地 SQLite

失效条件:
- 项目重新解析（schema_hash 变化）
- 手动清除缓存
```

## 7. 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/ai/complete-relations | AI 关系补全 |
| POST | /api/projects/{id}/ai/complete-comments | AI 注释补全 |
| POST | /api/projects/{id}/ai/generate-doc | AI 生成文档 |
| GET | /api/projects/{id}/ai/status | 查询项目的 AI 处理状态 |
| POST | /api/ai/cache/clear | 清除语义缓存 |

## 8. 验收标准

- [ ] 已有关联外键的表不会重复推荐
- [ ] 对有显式命名模式（`_id` 后缀）的表，准确率 > 85%
- [ ] 对完全无关联线索的表，不强行捏造关系（输出空列表）
- [ ] 中文注释建议质量可读可用
- [ ] 单次关系补全 API 调用 < 15s（含 AI 响应时间）
- [ ] 缓存命中时响应 < 500ms
- [ ] AI 功能可随时启停，不影响规则引擎运行
