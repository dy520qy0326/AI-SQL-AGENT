---
name: 10-graph-table-filter-tasks
title: 关系图表筛选（多选）— 任务分解
status: ARCHIVED
created: 2026-04-29
---

## 前置条件

- [x] Spec 已 REVIEWED
- [x] Plan 已 REVIEWED

## 任务列表

### Task 1: 后端 `build_graph` 增加 table_ids 过滤

**文件:** `backend/app/viz/graph.py`

**交付标准:**
- `build_graph()` 函数签名新增 `table_ids: set[str] | None = None` 参数
- 当 `table_ids` 不为 None 时，执行 1-hop 扩展：
  - 获取项目所有 relations
  - 找出与种子表有直接关联的邻居表（source 或 target 在种子集合中）
  - 最终节点 = 种子 ∪ 邻居
  - 边 = 两端都在最终节点集合内的所有边
- `table_ids` 为 None 时行为完全不变

**验收条件:**
- [ ] 不传 `table_ids` 时返回全部表和边
- [ ] 传一个表 ID 时，返回该表 + 所有关联表 + 它们之间的边
- [ ] 传多个表 ID 时，返回这些表 + 它们的邻居 + 相关边

---

### Task 2: 后端 `/graph` API 增加 table_ids 查询参数

**文件:** `backend/app/api/graph.py`

**交付标准:**
- `get_graph()` 新增 `table_ids: str | None = Query(None, alias="table_ids")`
- 有值时按 `,` 分割为 `set[str]` 传给 `build_graph`
- 空字符串或全空白时等同于 None

**验收条件:**
- [ ] `GET /api/projects/{id}/graph?table_ids=a,b,c` 返回过滤后的结果
- [ ] `GET /api/projects/{id}/graph`（不传参数）返回全部结果

---

### Task 3: 后端 `build_mermaid` 增加 table_ids 过滤

**文件:** `backend/app/viz/mermaid.py`

**交付标准:**
- `build_mermaid()` 函数签名新增 `table_ids: set[str] | None = None` 参数
- 过滤逻辑与 `build_graph` 一致：1-hop 扩展

**验收条件:**
- [ ] 不传 `table_ids` 时 Mermaid 输出不变
- [ ] 传 `table_ids` 时输出种子表 + 邻居表的实体和关系

---

### Task 4: 后端 `/mermaid` API 增加 table_ids 查询参数

**文件:** `backend/app/api/graph.py`

**交付标准:**
- `get_mermaid()` 同步增加 `table_ids` 查询参数，传给 `build_mermaid`

**验收条件:**
- [ ] `GET /api/projects/{id}/mermaid?table_ids=a,b,c` 返回过滤后的 Mermaid 文本
- [ ] `GET /api/projects/{id}/mermaid` 返回全部

---

### Task 5: 前端 `useGraph` / `useMermaid` hook 增加 tableIds 参数

**文件:** `frontend/src/hooks/useGraph.ts`

**交付标准:**
- `GraphParams` 接口增加 `tableIds?: string[]`
- 有值时拼入 query string（逗号分隔）
- `useMermaid` 同步增加 `tableIds` 参数
- `queryKey` 包含 `tableIds` 以支持缓存区分

**验收条件:**
- [ ] 传 `tableIds: ['a','b']` 时请求 URL 包含 `table_ids=a,b`
- [ ] 不传时 URL 无 table_ids 参数
- [ ] 切换 tableIds 时触发重新请求

---

### Task 6: 前端 `TableSelect` 多选组件

**文件:** `frontend/src/components/TableSelect.tsx`（新建）

**交付标准:**
- 调用 `useTables(projectId)` 获取表列表
- 搜索过滤：输入时按表名（含 schema）模糊匹配
- 多选：勾选/取消勾选
- 显示已选数量 "已选 X/Y 个表"
- "清空"按钮一键重置
- Popover/dropdown 展开形式，不占页面固定空间
- 样式与 `RelationFilters` 组件保持一致（使用相同 Tailwind 类）

**验收条件:**
- [ ] 渲染项目所有表作为选项
- [ ] 搜索框可输入过滤表名
- [ ] 勾选、取消勾选正常
- [ ] 清空按钮已选表重置为 []
- [ ] 显示已选/总数
- [ ] dark mode 样式一致

---

### Task 7: 前端 `GraphView` 集成 TableSelect

**文件:** `frontend/src/pages/GraphView.tsx`

**交付标准:**
- 引入 `TableSelect` 组件，放置在筛选栏区域
- 状态: `const [tableIds, setTableIds] = useState<string[]>([])`
- 传递给 `useGraph` 和 `useMermaid`
- 项目 id 变化时重置 `tableIds` 为 `[]`

**验收条件:**
- [ ] TableSelect 出现在关系图页面筛选栏
- [ ] 选择表后力导向图更新
- [ ] 切换到 Mermaid 视图表筛选同样生效
- [ ] 切换项目后筛选重置
- [ ] 与现有 type / minConfidence 筛选协同工作
