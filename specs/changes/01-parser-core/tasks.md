---
status: REVIEWED
---

# Tasks: 01-parser-core — SQL DDL Parser 核心引擎

总计 11 个 Task，按依赖关系排列。

---

## Task 1：项目骨架和基础设施

**交付标准：**
- FastAPI 项目骨架可用，目录结构符合规范
- `requirements.txt` 包含所有依赖（fastapi、uvicorn、sqlglot、pydantic）
- Pydantic 输出模型（`Column`、`Index`、`ForeignKey`、`Table`、`ParseResult`）定义完成
- 基础 `main.py` 含健康检查端点 `GET /health`

**验收条件：**
- [ ] `uvicorn app.main:app` 启动无报错
- [ ] `GET /health` 返回 `{"status": "ok"}`
- [ ] Pydantic 模型可实例化且序列化为 JSON

**依赖：** 无

---

## Task 2：BaseParser + 语句分割 + 方言检测

**交付标准：**
- `BaseParser` 抽象基类定义 `parse()` 模板方法
- `_parse_statements()` 将 SQL 文本按 `CREATE` 关键字智能分割
- `_detect_dialect()` 实现方言自动检测逻辑
- `ParseResult` 返回基本结构（dialect + 空 tables + 错误列表）

**验收条件：**
- [ ] 多语句 SQL 文件被正确分割为独立语句
- [ ] 含 `AUTO_INCREMENT` 的文本被检测为 MySQL
- [ ] 含 `SERIAL` 的文本被检测为 PostgreSQL
- [ ] 空白文本不报错

**依赖：** Task 1

---

## Task 3：CREATE TABLE + 字段解析 + 主键

**交付标准：**
- 解析 `CREATE TABLE [schema.]name (...)` 提取表名和 schema
- 解析字段定义：名称、类型、长度/精度、NOT NULL、DEFAULT
- 识别 PRIMARY KEY（单列字段级 + 多列表级复合主键）
- 返回 `Table` 对象含正确字段列表

**验收条件：**
- [ ] `CREATE TABLE users (id INT NOT NULL)` → `name="users"`, columns 含 `{"name":"id","type":"int","nullable":false}`
- [ ] 复合主键 `PRIMARY KEY (a, b)` 对应的两个字段 `primary_key=true`
- [ ] 字段级 `PRIMARY KEY` 标记正确
- [ ] `DEFAULT` 值正确提取（数字、字符串、NULL）
- [ ] 有长度参数的类型正确解析：`VARCHAR(255)` → `type="varchar", length=255`
- [ ] `JSON`、`TEXT`、`BOOLEAN` 等无长度类型 → `length=null`

**依赖：** Task 2

---

## Task 4：外键解析

**交付标准：**
- 列级外键：`col INT REFERENCES ref_table(ref_col)`
- 表级外键：`FOREIGN KEY (cols) REFERENCES ref_table(ref_cols)`
- 复合外键：`FOREIGN KEY (a, b) REFERENCES ref(c, d)`

**验收条件：**
- [ ] 列级 `REFERENCES` 正确提取 `ref_table` 和 `ref_columns`
- [ ] 表级 `FOREIGN KEY` 约束正确提取 `columns`、`ref_table`、`ref_columns`
- [ ] 复合外键多列顺序正确
- [ ] 同一语句中多个外键全部提取

**依赖：** Task 3

---

## Task 5：索引解析

**交付标准：**
- 解析 `INDEX`、`KEY`、`UNIQUE INDEX`、`UNIQUE KEY`
- 提取索引名和索引包含的字段列表
- `unique` 标记正确

**验收条件：**
- [ ] `INDEX idx_name (col)` → `{"name":"idx_name","unique":false,"columns":["col"]}`
- [ ] `UNIQUE INDEX uq_email (email)` → `{"unique":true}`
- [ ] `KEY` 关键字作为 INDEX 的同义词处理
- [ ] 多列索引顺序正确

**依赖：** Task 3

---

## Task 6：MySQL 方言适配

**交付标准：**
- `MySQLParser` 继承 BaseParser，覆盖 MySQL 特有语法
- 支持 `AUTO_INCREMENT` 属性识别
- 支持 `` ` `` 反引号引用
- 支持 `ENGINE=`, `DEFAULT CHARSET` 等表选项（忽略但不出错）
- 支持 `COMMENT 'xxx'` 字段/表注释提取
- 支持 `TINYINT`, `BIGINT`, `DATETIME` 等 MySQL 特有类型

**验收条件：**
- [ ] 字段 `id INT AUTO_INCREMENT` → `auto_increment=true`（在 Column 模型中新增字段）
- [ ] `` `user``name` `` 正确识别为 `user-name`
- [ ] `COMMENT '用户表'` 提取到 `comment`
- [ ] 含 `ENGINE=InnoDB` 的 DDL 解析无报错
- [ ] 需将 `Column` 模型增加 `auto_increment: bool = False` 字段

**依赖：** Tasks 3, 4, 5

---

## Task 7：PostgreSQL 方言适配

**交付标准：**
- `PostgreSQLParser` 继承 BaseParser，覆盖 PG 特有语法
- 支持 `SERIAL`, `BIGSERIAL` 类型（等价于自增）
- 支持 `"` 双引号引用
- 支持 `::type` 类型转换语法（忽略）
- 支持 PG 特有类型：`UUID`, `JSONB`, `TIMESTAMPTZ`, `BYTEA`
- 支持 `COMMENT ON TABLE/COLUMN` 语法

**验收条件：**
- [ ] `id SERIAL PRIMARY KEY` → `type="integer"`, `auto_increment=true`
- [ ] `"user name"` 正确识别为 `user name`
- [ ] `COMMENT ON TABLE users IS '用户表'` 提取到表 comment
- [ ] `UUID`, `JSONB` 类型正确提取

**依赖：** Tasks 3, 4, 5

---

## Task 8：错误处理与容错

**交付标准：**
- 语法错误语句被跳过，错误信息加入 `ParseResult.errors`
- 每条错误记录包含语句索引、行号和错误描述
- 少量非关键错误不影响整个解析流程
- 空文件/空输入返回空 `tables` + `errors`，不崩溃

**验收条件：**
- [ ] 含非法 SQL 的 DDL 正常返回正确语句的解析结果
- [ ] `errors` 列表不为空且条目包含 `statement_index`、`line`、`message`
- [ ] 空字符串输入不报异常
- [ ] 仅含注释/空行的文件返回空结果

**依赖：** Tasks 6, 7

---

## Task 9：MySQL 标准样本测试

**交付标准：**
- 准备 MySQL employees.sql 等标准 DDL 样本
- 用 `MySQLParser` 解析全部样本，结果与预期结构对照
- 参数化 pytest 用例覆盖样本中的每张表

**验收条件：**
- [ ] employees.sql 的 8 张表全部正确解析
- [ ] 所有外键关系 100% 匹配
- [ ] 所有字段类型和约束 100% 准确
- [ ] 解析 500 行 DDL 耗时 < 500ms

**依赖：** Tasks 6, 8

---

## Task 10：PostgreSQL DDL 样本测试

**交付标准：**
- 准备 PostgreSQL 标准 DDL 样本（如 pagila 或自定义样本）
- 用 `PostgreSQLParser` 解析全部样本
- 参数化 pytest 用例覆盖

**验收条件：**
- [ ] 所有表正确解析
- [ ] SERIAL 类型正确映射为自增
- [ ] PG 特有类型正确识别
- [ ] 解析耗时 < 500ms（500 行）

**依赖：** Tasks 7, 8

---

## Task 11：边界测试

**交付标准：**
- 覆盖以下边界场景的 pytest 测试用例：
  - 空文件 / 纯注释文件 / 纯空白文件
  - 含语法错误的 DDL（漏括号、错关键字）
  - 大文件（1000+ 行 DDL）
  - 未知方言的回退行为
  - 同一文件混合多个 `CREATE TABLE` + 无效语句
  - 含特殊字符的表名/字段名

**验收条件：**
- [ ] 所有边界用例不崩溃
- [ ] 大文件解析可接受时间内完成（2000 行 < 2s）
- [ ] 单元测试覆盖率 > 85%
- [ ] 所有测试通过

**依赖：** Tasks 9, 10
