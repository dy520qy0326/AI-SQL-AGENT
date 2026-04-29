---
name: 统一项目卡片高度 — 技术方案
status: REVIEWED
created: 2026-04-29
---

# 统一项目卡片高度 — 技术方案

## 变更范围

| 项目 | 内容 |
|------|------|
| 涉及文件 | `frontend/src/components/ProjectCard.tsx` |
| 涉及模块 | 前端 UI — 项目卡片组件 |
| 影响范围 | 仅 ProjectCard 组件，无下游影响 |
| 回滚方案 | git checkout 恢复文件 |

## 实现方案

### 改动说明（逐行）

**文件：** `frontend/src/components/ProjectCard.tsx`

**① Link 元素 — 添加 flex 布局类**

```diff
- className="block rounded-lg border bg-white p-5 shadow-sm transition hover:shadow-md hover:border-blue-200 no-underline"
+ className="block rounded-lg border bg-white p-5 shadow-sm transition hover:shadow-md hover:border-blue-200 no-underline flex flex-col h-full"
```

**② 标题 h3 — 添加 title 属性（悬浮显示完整标题）**

```diff
- <h3 className="text-base font-semibold text-gray-900 mb-2 truncate">
+ <h3 className="text-base font-semibold text-gray-900 mb-2 truncate" title={project.name}>
```

**③ 描述区域 — 外层包裹占位容器，移除 p 标签的 margin**

创建始终渲染的描述区容器，使用 `min-h-[2.5rem]` 保留 2 行文本的空间：

```diff
- {project.description && (
-   <p className="text-sm text-gray-500 mb-3 line-clamp-2">
-     {project.description}
-   </p>
- )}
+ <div className="min-h-[2.5rem] mb-3">
+   {project.description && (
+     <p className="text-sm text-gray-500 line-clamp-2" title={project.description}>
+       {project.description}
+     </p>
+   )}
+ </div>
```

关键变化：
- 容器始终渲染，无论是否有描述
- `min-h-[2.5rem]` 保留 2 行 text-sm 文本的垂直空间
- `mb-3` 从 p 标签移到容器上，保证间距统一
- p 标签内 `title={project.description}` 实现悬浮 tooltip

**④ 统计信息区 — 添加 mt-auto 固定到底部**

```diff
- <div className="flex items-center gap-4 text-xs text-gray-400">
+ <div className="flex items-center gap-4 text-xs text-gray-400 mt-auto">
```

### 最终 DOM 结构

```html
<Link flex flex-col h-full>         <!-- 弹性列布局，填满网格 -->
  <h3 truncate title={name}>        <!-- 标题 -->
  <div min-h-[2.5rem] mb-3>         <!-- 描述区占位容器（始终渲染） -->
    <p line-clamp-2>?                <!-- 描述文本（条件渲染） -->
  </div>
  <div mt-auto>                      <!-- 统计信息（固定底部） -->
    ...table_count / relation_count / date...
  </div>
</Link>
```

所有卡片统一布局：标题 → [固定最小高度占位] → [弹性空间] → 统计信息

## 风险分析

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| `line-clamp-2` 在 flex 子元素中失效 | 低 | 描述不截断 | 已在 `<p>` 上使用 `line-clamp-2`，p 为块级元素不受 flex 影响 |
| `h-full` 在 grid 外单测环境失效 | 低 | 测试渲染差异 | 单测中 grid container 未模拟时不影响功能 |
| 描述区 `min-h` 预留过多/过少空间 | 中 | 视觉偏差 | 基于 `text-sm` 的 `line-height: 1.25rem` 精确计算：2 行 = 2.5rem |
| 浏览器兼容性（rem 计算） | 低 | 不影响 | rem 为 CSS 标准单位，所有现代浏览器支持 |

## 工作量估算

| 步骤 | 耗时 |
|------|------|
| 编码改动（4 处） | ~5 min |
| 本地 dev server 验证 | ~5 min |
| 合计 | **~10 min** |

## 验证方案

由于 ProjectCard 无前端测试，采用人工视觉验证：

1. 启动 dev server：`cd frontend && npm run dev`
2. 在浏览器打开项目列表页
3. 验证清单：
   - [ ] 有描述 / 无描述的卡片在网格中等高
   - [ ] 描述超长时悬浮显示 tooltip
   - [ ] 描述较短的卡片，描述区占用空间与其他卡片一致
   - [ ] 统计信息栏在所有卡片底部对齐
   - [ ] hover 卡片时 shadow/border 效果正常
   - [ ] 点击卡片跳转正常
   - [ ] 响应式断点（缩小窗口至 1/2 列）卡高等高正常
   - [ ] 浏览器缩放 200% 布局正常

## 依赖

- 无新增依赖
- Tailwind CSS class 均为内置工具类
