# UI 设计规范 - 液态玻璃风格

## 设计决策

| 决策项 | 选择 | 说明 |
|--------|------|------|
| 视觉风格 | 液态玻璃 (Liquid Glass) | 2026年最前沿趋势 |
| 布局结构 | 双栏 + 浮动抽屉 | 左侧可折叠，右侧浮动 |
| Agent可视化 | 状态卡片组 | 横向排列，活跃发光 |
| 主色调 | 紫蓝渐变 (AI Tech) | 科技感强 |

## 视觉规范

### 颜色系统

```css
/* 主渐变背景 */
--gradient-primary: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.15));

/* 玻璃效果 */
--glass-bg: rgba(255, 255, 255, 0.5);
--glass-blur: backdrop-filter: blur(12px);
--glass-border: 1px solid rgba(255, 255, 255, 0.4);

/* Agent状态色 */
--agent-active: linear-gradient(135deg, #8b5cf6, #6366f1);
--agent-idle: #6b7280;
--agent-glow: box-shadow: 0 0 8px #a78bfa;

/* 文字色 */
--text-primary: #e0e7ff;
--text-secondary: #9ca3af;
--text-muted: #6b7280;
```

### 玻璃卡片样式

```css
.glass-card {
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 12px;
}
```

## 布局规范

### 整体结构

```
┌─────────────────────────────────────────────────────────┐
│ ┌──┐  Agent状态卡片组                                    │
│ │图│  [Coordinator●] [Profiler○] [Code Gen○]            │
│ │标│                                                     │
│ │区│  聊天消息区                           ┌──────────┐  │
│ │  │                                      │ 浮动抽屉 │  │
│ │可│  用户: 分析数据...                    │ 代码/图表 │  │
│ │折│                                      │   报告   │  │
│ │叠│  AI: 我已完成分析...                  └──────────┘  │
│ └──┘                                                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 输入框                                    [发送]    │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 左侧边栏 (可折叠)

- **折叠状态**: 60px宽，仅显示图标
- **展开状态**: 240px宽，显示会话列表
- **交互**: Hover自动展开，或点击固定展开

### 浮动抽屉 (右侧)

- **默认位置**: 右上角
- **尺寸**: 320px宽，自适应高度
- **功能**: 代码/图表/报告三个Tab
- **交互**: 可拖拽位置，可展开/收起

## Agent状态卡片

### 样式

```css
.agent-card {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(8px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.agent-card.active {
  background: rgba(139, 92, 246, 0.3);
  border-color: rgba(139, 92, 246, 0.4);
}

.agent-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.agent-indicator.active {
  background: #a78bfa;
  box-shadow: 0 0 8px #a78bfa;
  animation: pulse 2s infinite;
}
```

### Agent颜色映射

| Agent | 颜色 | 图标 |
|-------|------|------|
| coordinator | 紫色 #8b5cf6 | 🎯 |
| data_parser | 蓝色 #3b82f6 | 📄 |
| data_profiler | 青色 #06b6d4 | 🔍 |
| code_generator | 琥珀色 #f59e0b | 💻 |
| debugger | 橙色 #f97316 | 🔧 |
| visualizer | 粉色 #ec4899 | 📊 |
| report_writer | 靛蓝 #6366f1 | 📝 |

## 动画规范

### 过渡

```css
--transition-fast: 150ms ease;
--transition-normal: 250ms ease;
--transition-slow: 400ms ease;
```

### 脉冲动画

```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
```

## 文件修改清单

1. `frontend/src/app/globals.css` - 添加玻璃效果CSS变量和动画
2. `frontend/src/app/page.tsx` - 更新主布局结构
3. `frontend/src/components/sidebar/Sidebar.tsx` - 改为可折叠设计
4. `frontend/src/components/panel/RightPanel.tsx` - 改为浮动抽屉
5. `frontend/src/components/chat/ChatInterface.tsx` - 添加Agent状态卡片组
6. `frontend/src/components/chat/ExecutionPanel.tsx` - 移除或整合到状态卡片
