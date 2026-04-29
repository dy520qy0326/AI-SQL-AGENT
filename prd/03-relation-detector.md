# PRD: 关系检测模块 (Relation Detector)

## 1. 产品概述

Relation Detector 负责发现和构建数据库表之间的关联关系。它不仅提取 DDL 中显式定义的外键，还通过命名约定、字段类型匹配和 AI 辅助来推断潜在关系，最终输出统一的关系图谱。

## 2. 目标用户

- **直接用户**：DBA、数据分析师需要理解库表之间的数据流向
- **下游消费者**：可视化模块、AI 问答模块

## 3. 功能需求

### P0 — 显式外键提取

| 功能 | 说明 |
|------|------|
| 列级外键 | `col_name REFERENCE other_table(id)` 精确提取 |
| 表级外键 | `FOREIGN KEY (col) REFERENCES other_table(id)` |
| 复合外键 | 多列组合外键的正确分组 |
| 自引用外键 | 外键指向自身表（如树形结构） |

### P1 — 隐式关系推断

| 功能 | 说明 |
|------|------|
| 命名推断 | `order.user_id` → 匹配 `user.id`（`_id` 后缀规则） |
| 同名字段匹配 | 同一 `project_id` 出现在两张表且类型一致，推断关联 |
| 类型匹配 | 字段名不同但语义相同 + 类型一致，如 `uid` ↔ `user_id` |
| 中间表识别 | 包含两个外键且只有 3 个字段的表，识别为 N:M 关联 |
| 置信度打分 | 每条推断关系附带 0~1 的置信度 |

### P2 — AI 辅助推断

| 功能 | 说明 |
|------|------|
| AI 关系补全 | 将剩余未关联的表提交 AI，分析表名/字段名/注释后举荐关系 |
| 人工确认闭环 | 前端可接受/拒绝/修改 AI 推荐的关系 |

## 4. 置信度评分规则

| 场景 | 置信度 | 说明 |
|------|--------|------|
| 显式外键 | 1.0 | DDL 明确声明 |
| `_id` 后缀精确匹配表名 | 0.85 | `order.user_id` → `user.id` |
| `_id` 后缀模糊匹配表名 | 0.70 | `order.creator_id` → `user.id` |
| 同名字段同类型 | 0.60 | 两个表都有 `org_id` 且类型一致 |
| 同名字段不同类型 | 0.30 | 字段名相同但类型不一致，低分但上报 |
| AI 推荐 | 0.35~0.80 | 取决于 AI 给出的理由充分度 |

**阈值策略**：置信度 < 0.6 的关系默认折叠在前端，需用户展开确认。

## 5. 关系环检测

```yaml
输入: 项目所有关系列表
输出: 环路径数组

环示例:
  A.user_id → B.id
  B.dept_id → C.id
  C.manager_id → A.id   # 闭合

处理: 标记环路径，在前端图中高亮显示
```

## 6. 输入 / 输出

### 输入
```
解析后的结构化元数据（tables[], columns[], foreign_keys[]）
```

### 输出
```json
[
  {
    "source_table": "orders",
    "source_columns": ["user_id"],
    "target_table": "users",
    "target_columns": ["id"],
    "relation_type": "FOREIGN_KEY",
    "confidence": 1.0,
    "source": "DDL explicit FK constraint: fk_orders_user"
  },
  {
    "source_table": "comments",
    "source_columns": ["post_id"],
    "target_table": "posts",
    "target_columns": ["id"],
    "relation_type": "INFERRED",
    "confidence": 0.85,
    "source": "naming convention: post_id → posts.id"
  }
]
```

## 7. 验收标准

- [ ] 显式外键提取率 100%（所有 DDL 中声明的 FK 全部检出）
- [ ] `_id` 命名推断准确率 > 90%
- [ ] N:M 中间表识别: 符合条件的中介表 100% 识别
- [ ] 同一张表不应出现重复的关系条目
- [ ] 置信度分级正确，前端可按阈值筛选
- [ ] 环检测正确标记所有循环引用
- [ ] 处理 200 张表的关系推断耗时 < 2s
