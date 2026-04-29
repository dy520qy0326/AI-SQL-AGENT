---
name: 统一项目卡片高度 — 任务分解
status: COMPLETED
created: 2026-04-29
---

# 统一项目卡片高度 — 任务分解

## Task 1：修改 ProjectCard 组件布局和 tooltip

| 属性 | 内容 |
|------|------|
| 涉及文件 | `frontend/src/components/ProjectCard.tsx` |
| 工作量 | ~10 min |
| 依赖 | 无 |

### 交付内容

4 处改动，按顺序执行：

**① Link 元素** — 追加 `flex flex-col h-full` class
**② h3** — 追加 `title={project.name}` 属性
**③ 描述区** — 包裹 `min-h-[2.5rem] mb-3` 容器，p 标签移除 `mb-3`，追加 `title={project.description}`
**④ 统计区 div** — 追加 `mt-auto` class

### 验收条件

- [ ] 有描述 / 无描述的卡片在网格行内完全等高
- [ ] 描述超长时鼠标悬浮显示完整内容的 tooltip
- [ ] 统计信息栏在所有卡片底部对齐
- [ ] 卡片 hover 效果（shadow、border）正常
- [ ] 点击卡片跳转到项目详情页正常
- [ ] 响应式断点（2 列 / 1 列）下卡等高一致
- [ ] 浏览缩放 200% 时布局无异常

### 验证步骤

```bash
# 启动后端
pipx run --venv fastapi uvicorn app.main:app --port 8199 &

# 启动前端（另一个终端）
cd frontend && npm run dev
```

浏览器打开 `http://localhost:5173/projects`，逐项验收。
