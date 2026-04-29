---
name: 01-parser-core
title: SQL DDL Parser 核心引擎
status: ARCHIVED
created: 2026-04-29
---

## 摘要

实现 SQL DDL 文件的结构化解析引擎，将 CREATE TABLE 语句解析为表、字段、约束、索引、外键等标准化元数据，作为整个系统的底层数据基础。

## 动机

所有上层功能（关系检测、可视化、AI 问答、文档生成）都依赖准确的结构化元数据。Parser 是技术栈中最底层的模块，优先实现以支撑后续开发。

## 范围

### 包含

- 单文件多语句分割与解析
- CREATE TABLE 解析：表名、schema、注释
- 字段定义解析：名称、数据类型、长度/精度、NOT NULL、DEFAULT
- 主键解析：单列及复合主键
- 外键解析：列级 REFERENCES 和表级 FOREIGN KEY 约束
- 索引解析：INDEX / UNIQUE INDEX / KEY
- MySQL 和 PostgreSQL 两种方言支持
- 语法容错：出错语句跳过 + 错误位置记录，不影响后续解析
- 结构化输出

### 不包含

- ENUM、AUTO_INCREMENT、CHECK、分区表等 P1/P2 特性（后续提案）
- 视图、触发器、存储过程解析
- SQLite 方言
- 隐式关系推断（由 Relation Detector 模块负责）
- AI 增强解析（由 AI Service 模块负责）

### 依赖

- PRD: `prd/01-parser-module.md`
- 第三方库：sqlglot（负责 SQL 词法/语法分析）
- 无其他内部模块依赖

## 规范

### 输入

| 条目 | 说明 |
|------|------|
| 内容 | 原始 SQL 文本字符串 |
| 方言 | 可选，`mysql` / `postgresql` / 空（自动检测） |
| 编码 | UTF-8 |

### 输出结构

解析器返回一个结构化的解析结果对象，包含以下顶层字段：

- `dialect` — 检测或指定的方言标识
- `tables` — 解析得到的表列表
- `errors` — 解析过程中的错误/警告列表（非空文件且无任何有效表时为空列表）

每张表包含：
- `name` — 表名
- `schema` — schema 名（未指定时为空字符串）
- `comment` — 表注释（无可用时为空字符串）
- `columns` — 字段列表
- `indexes` — 索引列表
- `foreign_keys` — 外键列表

每个字段包含：
- `name` — 字段名
- `type` — 数据类型（如 `int`、`varchar`）
- `length` — 长度/精度（无可用时为 null）
- `nullable` — 是否可为空
- `default` — 默认值（无可用时为 null）
- `primary_key` — 是否为主键的一部分
- `comment` — 字段注释（无可用时为空字符串）

每个索引包含：
- `name` — 索引名
- `unique` — 是否唯一索引
- `columns` — 索引包含的字段名列表

每个外键包含：
- `columns` — 当前表中参与外键的字段名列表
- `ref_table` — 引用表名
- `ref_columns` — 引用表中的字段名列表

### 错误处理

| 场景 | 行为 |
|------|------|
| 语法错误语句 | 跳过该语句，错误加入 `errors` 列表，继续解析 |
| 空文件 | 返回空 `tables` + 提示信息 |
| 未知方言 | 回退到自动检测 |
| 未知数据类型 | 保留原始类型字符串，标记告警 |
| 循环外键引用 | 正常解析（关系环由下游模块处理） |
| 分号缺失 | 按 `CREATE`/`CREATE TABLE` 关键字智能分割 |

## 验收标准

- [ ] MySQL 标准 DDL 样本的全部表正确解析，字段、类型、约束 100% 准确
- [ ] PostgreSQL DDL 样本全部表正确解析
- [ ] 单列/复合主键正确识别
- [ ] 列级外键（`REFERENCES`）和表级外键（`FOREIGN KEY () REFERENCES`）均正确识别
- [ ] UNIQUE 索引和普通 INDEX 区分正确
- [ ] 含语法错误的 DDL 正常跳过错误语句，`errors` 中包含行号及原因，不崩溃
- [ ] 空文件返回空结果而非报错
- [ ] 解析 500 行 DDL 耗时 < 500ms
- [ ] 单元测试覆盖率 > 85%

## 备注

- 本提案对应 Phase 1 的 P0 范围，P1/P2 特性留待后续提案
- sqlglot 已内置多方言支持，方言适配成本较低
