---
name: 08-dark-mode-tasks
title: 暗色模式 — 任务分解
status: REVIEWED
created: 2026-04-29
---

## 任务列表

### Task 1: 基础设施（useTheme Hook + CSS + 初始化）

**交付标准：**
- `useTheme.ts` hook 完成，导出 `{ theme, resolved, setTheme, toggle }`
- `globals.css` 添加 `@custom-variant dark` 覆盖为 class 策略
- `main.tsx` 初始化时读取 localStorage / 系统偏好，设置 `<html class="dark">`
- Layout header 中出现 Sun/Moon 切换按钮，点击后切换并持久化

**涉及文件：**
- `frontend/src/styles/globals.css` — 添加 dark variant + transition 基础样式
- `frontend/src/hooks/useTheme.ts` — 新建
- `frontend/src/main.tsx` — 初始化 theme
- `frontend/src/components/Layout.tsx` — 添加切换按钮 + 容器 dark 背景

**依赖：** 无

**验收条件：**
- [ ] 按钮点击亮/暗切换正常
- [ ] 刷新页面偏好保持
- [ ] 首次访问跟随系统偏好
- [ ] `<html>` 上有正确的 `dark` class 切换

---

### Task 2: Layout 通用组件暗色适配

**交付标准：**
Layout 容器、导航、Tab 等所有页面共享组件的暗色样式就绪。

**涉及文件：**
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/NavTabs.tsx`
- `frontend/src/components/ProjectLayout.tsx`

**依赖：** Task 1

**验收条件：**
- [ ] NavTabs 选中/未选中状态在暗色下有正确配色
- [ ] ProjectLayout 布局背景正确
- [ ] 切换页面时保持暗色

---

### Task 3: 项目列表 + 项目详情暗色适配

**涉及文件：**
- `frontend/src/pages/ProjectList.tsx`
- `frontend/src/components/ProjectCard.tsx`
- `frontend/src/pages/ProjectDetail.tsx`
- `frontend/src/components/StatsPanel.tsx`
- `frontend/src/components/SqlUploader.tsx`
- `frontend/src/components/ConfirmDialog.tsx`

**依赖：** Task 2

**验收条件：**
- [ ] 项目列表页全部元素暗色正确
- [ ] 项目卡片 hover 效果正常
- [ ] 新建项目弹窗暗色正确
- [ ] 删除确认弹窗暗色正确
- [ ] 搜索框、上传区域暗色正确
- [ ] 统计面板暗色正确

---

### Task 4: 表结构视图暗色适配

**涉及文件：**
- `frontend/src/pages/TablesView.tsx`
- `frontend/src/pages/TableDetail.tsx`
- `frontend/src/components/ColumnTable.tsx`
- `frontend/src/components/ForeignKeyTable.tsx`
- `frontend/src/components/IndexTable.tsx`

**依赖：** Task 2

**验收条件：**
- [ ] 表列表页暗色正确
- [ ] 表详情页（字段/外键/索引表格）暗色正确
- [ ] 表格行 hover、斑马纹在暗色下表现正常

---

### Task 5: 关系图暗色适配

**涉及文件：**
- `frontend/src/pages/GraphView.tsx`
- `frontend/src/components/ErGraph.tsx`
- `frontend/src/components/GraphLegend.tsx`
- `frontend/src/components/RelationFilters.tsx`

**依赖：** Task 2

**特殊说明：**
- `ErGraph.tsx` 中的 ForceGraph 需根据暗色模式动态设置 `backgroundColor`、节点颜色、文字颜色
- `GraphLegend` 图例使用 `dark:` 变体

**验收条件：**
- [ ] ER 图在暗色模式下背景、节点、连线、标签均可见
- [ ] 图例暗色正确
- [ ] 关系筛选器暗色正确

---

### Task 6: AI 对话暗色适配

**涉及文件：**
- `frontend/src/pages/AiChat.tsx`
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/components/ChatMessage.tsx`
- `frontend/src/components/SessionList.tsx`

**依赖：** Task 2

**验收条件：**
- [ ] 对话列表暗色正确
- [ ] 用户/AI 消息气泡暗色区分明显
- [ ] 输入框暗色正确
- [ ] 会话侧边栏暗色正确

---

### Task 7: 文档 + 版本 + Diff 暗色适配

**涉及文件：**
- `frontend/src/pages/DocsView.tsx`
- `frontend/src/pages/DocPreview.tsx`
- `frontend/src/components/MarkdownViewer.tsx`
- `frontend/src/pages/VersionsView.tsx`
- `frontend/src/components/VersionSelector.tsx`
- `frontend/src/pages/DiffView.tsx`
- `frontend/src/components/DiffList.tsx`

**依赖：** Task 2

**验收条件：**
- [ ] 文档列表页暗色正确
- [ ] Markdown 渲染内容（标题、代码块、引用等）暗色正确
- [ ] 版本列表暗色正确
- [ ] Diff 视图暗色正确

---

## 执行顺序

```
Task 1 (基础设施)
  └── Task 2 (Layout 通用组件)
        ├── Task 3 (项目列表/详情)
        ├── Task 4 (表结构视图)
        ├── Task 5 (关系图)
        ├── Task 6 (AI 对话)
        └── Task 7 (文档/版本/Diff)
```

Task 3-7 相互独立，完成 Task 2 后可并行实现。
