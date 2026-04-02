# 文档目录

本目录包含项目的完整文档。

## 📚 文档列表

### 核心文档

- **[skills.md](skills.md)** - 技能系统文档
  - 所有可用技能的详细说明
  - 技能格式标准和开发指南
  - 智能体集成矩阵
  - 技能选择指南

### 部署文档

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - 部署指南
  - 环境配置
  - 依赖安装
  - 启动步骤
  - 常见问题

### 开发文档

- **[skills-refactoring-summary.md](skills-refactoring-summary.md)** - 技能体系重构总结
  - 重构完成的工作
  - 新的技能架构
  - 测试验证结果
  - 后续优化方向

---

## 📖 文档使用指南

### 对于开发者

如果你想：
- **了解技能系统** → 阅读 [skills.md](skills.md)
- **开发新技能** → 阅读 [skills.md](skills.md) 中的"开发新技能"章节
- **理解架构变更** → 阅读 [skills-refactoring-summary.md](skills-refactoring-summary.md)

### 对于用户

如果你想：
- **部署项目** → 阅读 [DEPLOYMENT.md](DEPLOYMENT.md)
- **了解可用技能** → 阅读 [skills.md](skills.md) 中的技能列表
- **选择合适技能** → 阅读 [skills.md](skills.md) 中的"技能选择指南"

---

## 🗂️ 技能目录结构

```
skills/
├── builtin/              # 内置技能（核心数据分析）
│   ├── describe_statistics/
│   ├── distribution_analysis/
│   ├── correlation_analysis/
│   ├── categorical_analysis/
│   └── outlier_detection/
├── anthropics/           # Claude 官方技能
│   ├── xlsx/
│   ├── pdf/
│   └── docx/
├── hoodini/             # 社区技能
│   └── analytics-metrics/
└── examples/            # 示例技能
    └── time-series-analysis/
```

---

## 📝 文档更新记录

| 日期 | 文档 | 更新内容 |
|------|------|---------|
| 2026-04-02 | skills.md | 重写以反映新的技能体系 |
| 2026-04-02 | skills-refactoring-summary.md | 创建重构总结文档 |
| 2026-04-02 | README.md | 创建文档目录说明 |
| 2026-03-30 | DEPLOYMENT.md | 初始部署文档 |

---

## 🔗 相关链接

- 项目根目录: [..](..)
- 源代码: [../src](../src)
- 测试: [../tests](../tests)
- 技能目录: [../skills](../skills)

---

*最后更新: 2026-04-02*
