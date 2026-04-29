---
name: 项目列表分页调整为每页 12 条 — 任务分解
status: COMPLETED
created: 2026-04-29
---

# 项目列表分页调整为每页 12 条 — 任务分解

## Task 1：修改前后端分页默认值

| 属性 | 内容 |
|------|------|
| 涉及文件 | `frontend/src/pages/ProjectList.tsx`、`backend/app/api/projects.py` |
| 工作量 | ~5 min |
| 依赖 | 无 |

### 交付内容

两处数值变更：
1. 前端 `ProjectList.tsx` → `size = 20` 改为 `size = 12`
2. 后端 `projects.py` → `size: int = 20` 改为 `size: int = 12`

### 验收条件

- [ ] 项目列表每页显示 12 个项目（3 列 × 4 行）
- [ ] 分页控件显示正确的页码和总数
- [ ] 翻页功能正常
- [ ] 搜索过滤不受影响
- [ ] 前端构建无报错

### 验证步骤

```bash
cd frontend && npm run build   # 确认无编译错误
```
打开浏览器确认每页 12 条。
