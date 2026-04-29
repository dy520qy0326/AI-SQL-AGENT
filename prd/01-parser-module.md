# PRD: SQL Parser 模块

## 1. 产品概述

SQL Parser 是整个系统的核心底层模块，负责将用户上传的 DDL（Data Definition Language）SQL 文件解析为结构化元数据，提取表、字段、约束、索引、外键等完整 schema 信息。

## 2. 目标用户

- **直接用户**：后端开发、DBA 上传历史 DDL 脚本
- **下游消费者**：Relation Detector、AI Service、Visualization 各模块

## 3. 功能需求

### P0 — 基础 DDL 解析

| 功能 | 说明 |
|------|------|
| CREATE TABLE 解析 | 提取表名、schema、comment |
| 字段定义解析 | 字段名、数据类型、长度/精度、NOT NULL、DEFAULT |
| 主键解析 | 单列/多列复合主键 |
| 外键解析 | 列级 REFERENCES、表级 FOREIGN KEY (...) REFERENCES ... |
| 索引解析 | INDEX / UNIQUE INDEX / KEY，包含索引列 |

### P1 — 增强解析

| 功能 | 说明 |
|------|------|
| 枚举类型处理 | ENUM 解析为允许值列表 |
| 自增属性 | AUTO_INCREMENT / SERIAL / IDENTITY 识别 |
| CHECK 约束 | 识别并记录 CHECK 约束表达式 |
| 表/字段注释 | COMMENT 提取，作为后续 AI 补全的基础 |
| 分区表信息 | PARTITION BY ... 识别 |

### P2 — 高级支持

| 功能 | 说明 |
|------|------|
| 视图解析 | CREATE VIEW ... AS SELECT ... 提取视图依赖 |
| 触发器/存储过程解析 | 仅识别声明，不做完整语法树分析 |
| 多语句拆分 | 一个文件中包含多条 CREATE 语句的拆分 |

## 4. 方言支持矩阵

| 特性 | MySQL | PostgreSQL | SQLite |
|------|-------|------------|--------|
| CREATE TABLE | ✅ | ✅ | ✅ |
| 数据类型 | ✅ | ✅ | ✅ |
| PRIMARY KEY | ✅ | ✅ | ✅ |
| FOREIGN KEY | ✅ | ✅ | ✅ |
| INDEX/UNIQUE | ✅ | ✅ | ✅ |
| COMMENT | ✅ | ✅ | ❌ |
| AUTO_INCREMENT | ✅ | ✅ (SERIAL) | ✅ |
| ENUM | ✅ | ✅ | ❌ |
| PARTITION | ✅ | ❌ | ❌ |
| CHECK | ✅ | ✅ | ✅ |

## 5. 输入 / 输出

### 输入
```
原始 SQL 文本（.sql 文件内容）
方言标识（可选，默认自动检测）
```

### 输出
```json
{
  "dialect": "mysql",
  "tables": [
    {
      "name": "users",
      "schema": "public",
      "comment": "用户表",
      "columns": [
        {
          "name": "id",
          "type": "int",
          "length": 11,
          "nullable": false,
          "default": null,
          "primary_key": true,
          "auto_increment": true,
          "comment": "主键ID"
        }
      ],
      "indexes": [
        {
          "name": "idx_email",
          "unique": true,
          "columns": ["email"]
        }
      ],
      "foreign_keys": [
        {
          "columns": ["dept_id"],
          "ref_table": "departments",
          "ref_columns": ["id"]
        }
      ]
    }
  ]
}
```

## 6. 异常处理

| 场景 | 行为 |
|------|------|
| 语法错误 | 跳过错误语句，记录错误位置 + 原因，继续解析后续语句 |
| 未知数据类型 | 保留原始类型字符串，标记为 `unknown_type` 并告警 |
| 循环外键引用 | 正常解析，由关系层做环检测 |
| 空文件 | 返回空列表，前端提示"未检测到有效 DDL" |
| 分号缺失 | 尝试智能断句，按换行+CREATE 关键字分割 |
| 引号/反引号不规范 | sqlglot 自动处理方言引号规则 |

## 7. 验收标准

- [ ] 标准 MySQL sample DDL（如 employees.sql）的 8 张表全部正确解析
- [ ] 字段类型、长度、NULL 约束 100% 准确
- [ ] 外键关系 100% 匹配（列级 + 表级）
- [ ] 复合主键正确识别
- [ ] 解析 500 行 DDL 耗时 < 500ms
- [ ] 语法错误时返回具体行号和错误原因，不崩溃
- [ ] 方言自动检测准确率 > 90%
- [ ] 单元测试覆盖率 > 85%
