To videos, just a moment that. Shura, we are 4 missions. No. ---
name: 09-embed-mermaid-er
title: 内嵌 Mermaid ER 图渲染
status: REVIEWED
created: 2026-04-29
---

## 摘要

当前前端 GraphView 页面仅有力导向图一种可视化方式，Mermaid 文本需要用户点击"复制"后粘贴到外部工具查看。本提案在项目关系图页面内嵌渲染 Mermaid ER 图，让用户在不离开页面的情况下获得第二种关系可视化视图。

## 动机

- 力导向图适合探索性交互（拖拽、悬停高亮），但无法看清每个表的完整字段结构
- Mermaid erDiagram 将表的所有列（含 PK/FK 标注）和关系一次性展开，适合全局浏览和文档截图
- 当前"复制 Mermaid"按钮要求用户有外部渲染环境（如 GitHub、Notion），体验割裂
- 内嵌 Mermaid 渲染后，用户在同一个页面内即可切换两种视图，互补使用

## 范围

### 包含

- 安装 `mermaid` npm 包，封装 `MermaidRenderer` 组件
- GraphView 页面增加视图切换开关（力导向图 / Mermaid ER 图）
- 关系筛选（type、min_confidence）对 Mermaid 视图同样生效
- 支持暗色模式
- 初次渲染加载指示器，渲染失败回退
- Mermaid 文本源码仍可复制

### 不包含

- 编辑 Mermaid 文本
- 导出为图片（可使用浏览器截图代替）
- 节点点击跳转（Mermaid 不原生支持点击交互）

## 验收标准

- [ ] Mermaid ER 图在页面内渲染为 SVG，所有表名、列名、PK/FK 标注、关系连线正确显示
- [ ] 视图切换在力导向图和 Mermaid 之间无闪烁
- [ ] 暗色模式下 Mermaid 主题同步切换
- [ ] 关系筛选（类型 + 置信度）切换后 Mermaid 视图同步更新
- [ ] 大型图（50+ 表）渲染顺畅，无明显卡顿
- [ ] Mermaid 渲染出错时展示友好提示，不阻塞页面
- [ ] "复制 Mermaid"按钮在两种视图下均可用

## 技术方案概要

- 使用官方 `mermaid` npm 包，`mermaid.render()` 将文本渲染为 SVG
- 封装 `MermaidDiagram` 组件，接收纯文本输入，输出内联 SVG
- 使用 `useEffect` 监听文本变化触发重新渲染
- 暗色模式通过 `mermaid.initialize({ theme: 'dark' })` 实现
- 通过 `mermaid.parse()` 预校验文本有效性，提前捕获语法错误
