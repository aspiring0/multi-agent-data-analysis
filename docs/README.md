# 多 Agent 数据分析平台 - 文档中心

## 快速导航

| 分类 | 说明 | 文档 |
|-----|------|------|
| **架构设计** | 系统架构和技术选型 | [查看 →](architecture/) |
| **部署指南** | 部署和配置 | [查看 →](deployment/) |
| **开发指南** | 开发和调试 | [查看 →](development/) |
| **技能系统** | 技能开发和配置 | [查看 →](skills/) |
| **解决方案** | 工程化方案对比 | [查看 →](solutions/) |

---

## 快速开始

### 1. 环境要求
- Python 3.10+
- Node.js 18+
- PostgreSQL (Docker)
- Conda (推荐)

### 2. 启动服务

```bash
# 启动 PostgreSQL
docker-compose up -d postgres

# 启动后端
conda activate multi_agent
python -m uvicorn backend.api.main:app --reload --port 8000

# 启动前端
cd frontend && npm run dev
```

### 3. 访问应用
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

## 文档目录结构

```
docs/
├── README.md                 # 本文档（文档索引）
├── architecture/             # 架构设计
│   └── fullstack-progress.md # 全栈架构改造进度
├── deployment/               # 部署指南
│   └── DEPLOYMENT.md         # 部署文档
├── development/              # 开发指南
│   └── backend-validation-guide.md
├── skills/                   # 技能系统
│   ├── skills.md             # 技能核心文档
│   └── skills-refactoring-summary.md
├── solutions/                # 工程化方案
│   └── production-solutions.md
└── troubleshooting/          # 故障排除（待创建）
```

---

## 按角色查找文档

### 对于开发者
- [技能系统文档](skills/skills.md) - 了解技能开发和配置
- [后端验证指南](development/backend-validation-guide.md) - 开发验证流程
- [全栈架构进度](architecture/fullstack-progress.md) - 架构改造详情

### 对于运维
- [部署指南](deployment/DEPLOYMENT.md) - 部署和配置
- [生产化方案](solutions/production-solutions.md) - 技术选型对比

### 对于用户
- 使用前端界面上传数据文件
- 用自然语言描述分析需求
- 查看分析结果和生成的代码

---

## 常见问题

### 端口被占用
```bash
# 查找占用端口的进程
netstat -ano | findstr :3000
# 终止进程
taskkill /PID <进程ID> /F
```

### PostgreSQL 连接失败
```bash
# 检查 Docker 容器状态
docker ps
# 重启 PostgreSQL
docker-compose restart postgres
```

### 前端依赖问题
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 技能目录结构

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

## 文档更新记录

| 日期 | 文档 | 更新内容 |
|------|------|---------|
| 2026-04-04 | README.md | 重组文档目录结构 |
| 2026-04-02 | skills.md | 重写以反映新的技能体系 |
| 2026-03-30 | DEPLOYMENT.md | 初始部署文档 |

---

## 相关链接

- [项目根目录](..)
- [源代码](../src)
- [测试](../tests)
- [技能目录](../skills)
- [前端代码](../frontend)

---

*最后更新：2026-04-04*
