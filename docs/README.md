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

### 环境要求
- Python 3.10+
- Node.js 18+
- Conda (推荐)
- Docker (可选，用于 PostgreSQL)

### 一键启动

```bash
# 1. 启动 PostgreSQL (Docker)
docker-compose up -d postgres

# 2. 启动后端 (新终端)
conda activate multi_agent
python -m uvicorn backend.api.main:app --reload --port 8000

# 3. 启动前端 (新终端)
cd frontend && npm run dev
```

### 访问地址

| 服务 | 地址 |
|-----|------|
| **前端界面** | http://localhost:3000 |
| **后端 API** | http://localhost:8000 |
| **API 文档** | http://localhost:8000/docs |

### 使用流程

1. 打开 http://localhost:3000
2. 点击 **"+"** 创建新会话
3. 上传数据文件 (CSV/Excel/JSON)
4. 输入分析需求，AI 自动分析

---

## 常见问题

### 端口被占用
```bash
# 查找并终止占用端口的进程
netstat -ano | findstr :3000
taskkill /PID <进程ID> /F
```

### PostgreSQL 连接失败
```bash
docker-compose restart postgres
```

### 会话不存在
现已自动修复 - 系统会自动创建缺失的会话

---

## 文档分类

### 架构设计
- [全栈架构进度](architecture/fullstack-progress.md) - FastAPI + Next.js 改造

### 部署指南
- [部署指南](deployment/DEPLOYMENT.md) - 多种部署方式

### 开发指南
- [后端验证指南](development/backend-validation-guide.md) - 功能验证清单

### 技能系统
- [技能文档](skills/skills.md) - 技能体系核心
- [重构总结](skills/skills-refactoring-summary.md) - 技能重构记录

### 解决方案
- [生产解决方案](solutions/production-solutions.md) - 技术选型对比

---

## 技能目录结构

```
skills/
├── builtin/              # 内置技能
│   ├── describe_statistics/
│   ├── distribution_analysis/
│   └── ...
├── anthropics/           # Claude 官方技能
└── examples/            # 示例技能
```

---

*最后更新：2026-04-04*
