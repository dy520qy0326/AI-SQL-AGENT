---
name: 项目列表分页调整为每页 12 条 — 技术方案
status: REVIEWED
created: 2026-04-29
---

# 项目列表分页调整为每页 12 条 — 技术方案

## 变更范围

| 项目 | 内容 |
|------|------|
| 涉及文件 | `frontend/src/pages/ProjectList.tsx`、`backend/app/api/projects.py` |
| 改动类型 | 常量值变更（20 → 12） |
| 影响范围 | 仅项目列表分页，无下游影响 |
| 回滚方案 | git checkout 恢复文件 |

## 改动说明

### ① 前端 — `ProjectList.tsx:16`

```diff
- const size = 20
+ const size = 12
```

此值传递给 `useProjects(page, size)` hook，作为 API 请求的 `size` query parameter。

### ② 后端 — `projects.py:59`

```diff
- async def list_projects(page: int = 1, size: int = 20):
+ async def list_projects(page: int = 1, size: int = 12):
```

后端默认值同时作为 API schema 的 OpenAPI 文档默认值。客户端仍可通过 `?size=` 覆盖（向后兼容）。

## 自动适配说明

以下逻辑无需改动，因为它们的计算依赖于后端返回的 `total` 值，会随 page size 自动调整：

- 分页控件显示 `"第 X / Y 页（共 Z 个）"` — 后端返回的 `total` 不变，`Y = ceil(total / size)`
- `data.total > size` 判断是否显示分页控件 — 使用当前 size 值
- 搜索过滤 — 纯客户端过滤，不涉及分页

## 工作量

| 步骤 | 耗时 |
|------|------|
| 编码（2 处数值修改） | ~2 min |
| 编译验证 | ~2 min |
| 合计 | **~5 min** |

## 验证方式

1. 启动前后端
2. 打开项目列表页，确认每页显示 12 个项目
3. 翻页确认分页控件正常
