---
name: 10-graph-table-filter-plan
title: 关系图表筛选（多选）— 技术方案
status: ARCHIVED
created: 2026-04-29
---

## 架构影响分析

**影响范围：** 后端 2 个 API 端点 + 2 个构建函数 + 前端 1 个 hook + 1 个新组件 + 1 个页面

```
后端                             前端
─────────────────               ─────────────────
GET /graph          ◄───         useGraph({ tableIds })
  └─ build_graph()    table_ids    └─ TableSelect 组件
GET /mermaid        ◄───         useMermaid({ tableIds })
  └─ build_mermaid()  table_ids
```

- 无数据库 schema 变更 — 筛选在应用层做，不新增查询
- 无新 API 端点 — 仅在现有端点加可选 query param
- 无新增依赖 — 前端用现有 `/tables` 接口获取选项

## 实现路径

### Step 1: 后端 `build_graph` 增加 table_ids 过滤（种子扩展）

**文件:** `backend/app/viz/graph.py`

- `build_graph()` 新增可选参数 `table_ids: set[str] | None = None`
- 当指定 `table_ids` 时，执行**1-hop 扩展**逻辑：
  1. 获取项目所有 relations
  2. 找出所有与种子表有直接关系的邻居表 ID（source 或 target 在种子集合中）
  3. 最终节点集合 = 种子 ∪ 邻居
  4. 边集合 = 两端都在最终节点集合内的所有边
- `table_ids` 为 None 时保持现有行为（返回全部）

### Step 2: 后端 API `/graph` 增加 table_ids 查询参数

**文件:** `backend/app/api/graph.py`

- `get_graph()` 新增 `Query(None, alias="table_ids")` 参数，类型 `str | None`
- 有值时按逗号分割为 `set[str]` 传入 `build_graph`

### Step 3: 后端 `build_mermaid` 增加 table_ids 过滤（种子扩展）

**文件:** `backend/app/viz/mermaid.py`

- `build_mermaid()` 新增可选参数 `table_ids: set[str] | None = None`
- 同样的 1-hop 扩展逻辑，与 `build_graph` 一致

### Step 4: 后端 API `/mermaid` 增加 table_ids 查询参数

**文件:** `backend/app/api/graph.py`

- `get_mermaid()` 同步增加 `table_ids` 查询参数，传给 `build_mermaid`

### Step 5: 前端 `useGraph` / `useMermaid` hook 增加 tableIds 参数

**文件:** `frontend/src/hooks/useGraph.ts`

- `useGraph` 的 `GraphParams` 增加 `tableIds?: string[]`
- 有值时拼入 query string（如 `table_ids=id1,id2,id3`）
- `useMermaid` 同步增加 `tableIds` 参数

### Step 6: 前端 `TableSelect` 多选组件

**文件:** `frontend/src/components/TableSelect.tsx`（新建）

- 调用 `useTables(projectId)` 获取表列表
- 搜索过滤：输入文字时按表名模糊匹配
- 多选：勾选/取消，展示已选表数
- 清空按钮：一键重置所有选择
- 以 popover/dropdown 形式展示，不占页面主要空间
- 样式与 `RelationFilters` 组件保持一致

### Step 7: 前端 `GraphView` 集成

**文件:** `frontend/src/pages/GraphView.tsx`

- 引入 `TableSelect` 组件，放在筛选栏区域
- 状态：`const [tableIds, setTableIds] = useState<string[]>([])`
- 传递给 `useGraph` 和 `useMermaid`
- 切换项目时重置（依赖 `id` 变化重置 state）
- 展示已选表数/总表数（如 `已选 5/20`）

## 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 选了部分表后 + INFERRED 类型筛选 -> 可能无结果 | UX 稍差 | 已有空状态提示"没有匹配的关系"，足够 |
| 大量表（100+）时多选组件渲染卡顿 | 性能 | 使用虚拟列表或仅展示前 50 条+搜索过滤 |

## 工作量估算

| 步骤 | 文件 | 预估变更量 |
|------|------|-----------|
| 1. `build_graph` 过滤 | `backend/app/viz/graph.py` | ~10 行 |
| 2. API `/graph` 参数 | `backend/app/api/graph.py` | ~5 行 |
| 3. `build_mermaid` 过滤 | `backend/app/viz/mermaid.py` | ~10 行 |
| 4. API `/mermaid` 参数 | `backend/app/api/graph.py` | ~5 行 |
| 5. hooks 参数 | `frontend/src/hooks/useGraph.ts` | ~15 行 |
| 6. `TableSelect` 组件 | `frontend/src/components/TableSelect.tsx` | ~100 行 |
| 7. `GraphView` 集成 | `frontend/src/pages/GraphView.tsx` | ~20 行 |
| **合计** | | **~165 行** |
