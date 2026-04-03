# 多 Agent 数据分析平台

基于 **LangGraph** 的生产级多智能体数据分析平台，支持用户通过自然语言完成数据上传、探索分析、代码生成、图表展示与报告输出。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Next.js)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Sidebar    │  │   Chat      │  │ RightPanel  │              │
│  │  会话管理    │  │   界面      │  │  代码/图表   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket + REST API
┌──────────────────────────▼──────────────────────────────────────┐
│                    后端 API (FastAPI)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    LangGraph Agent 系统                           │
│  ┌───────────────────────────────────────────────────────┐       │
│  │                  Coordinator (调度中心)                 │       │
│  └────┬───────┬────────┬─────────┬──────────┬────────────┘       │
│       │       │        │         │          │                    │
│       ▼       ▼        ▼         ▼          ▼                    │
│    Data     Data    Code Gen  Visualizer  Report                 │
│    Parser   Profiler   │          │        Writer                │
│       │       │    ┌───┴───┐      │                              │
│       │       │    │Debugger│──────┘                              │
│       └───────┴────┴───────┴─────────────────────────────────────│
│                           │                                      │
│               ┌───────────▼───────────┐                          │
│               │   Skill Registry      │  13 个分析技能            │
│               │   Code Sandbox        │  安全执行环境             │
│               └───────────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    PostgreSQL (持久化)                            │
│         会话状态 + Checkpointer + 跨会话记忆                       │
└──────────────────────────────────────────────────────────────────┘
```

### 核心流程：代码生成 → 自动修复

```
CodeGenerator ──生成代码──▶ Sandbox 执行
                               │
                          成功? ──▶ 返回结果
                               │
                          失败? ──▶ Debugger ──修复代码──▶ Sandbox 重试
                                      ↑                        │
                                      └──── 最多重试 3 次 ─────┘
```

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| **前端** | Next.js 16 + React 19 + Zustand + Tailwind CSS |
| **后端** | FastAPI + LangGraph + DeepSeek V3 |
| **数据库** | PostgreSQL 16 |
| **部署** | Docker + Nginx |
| **测试** | pytest (后端) + Jest (前端) |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Docker (用于 PostgreSQL)

### 一键启动

```bash
# 1. 启动 PostgreSQL
docker-compose up -d postgres

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 启动后端 (新终端)
pip install -r requirements.txt
python -m uvicorn backend.api.main:app --reload --port 8000

# 4. 启动前端 (新终端)
cd frontend && npm install && npm run dev
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

## 生产部署

```bash
# 配置环境变量
cp .env.example .env.prod

# 一键部署
docker-compose -f docker-compose.prod.yml up -d --build

# 健康检查
./scripts/health_check.sh
```

详见 [部署文档](docs/deployment/DEPLOYMENT.md)

## 测试

```bash
# 后端测试
python -m pytest tests/ -v

# 前端测试
cd frontend && npm test
```

## 项目结构

```
multi-agent-data-analysis/
├── backend/                    # FastAPI 后端
│   └── api/
│       ├── main.py            # 应用入口
│       ├── routes/            # API 路由
│       └── websocket/         # WebSocket 处理
├── frontend/                   # Next.js 前端
│   └── src/
│       ├── components/        # UI 组件
│       ├── lib/               # 状态管理 + API
│       └── hooks/             # React Hooks
├── src/                        # LangGraph Agent 系统
│   ├── agents/                # 8 个 Agent
│   ├── graph/                 # StateGraph 定义
│   ├── skills/                # 13 个 Skill
│   ├── sandbox/               # 代码沙箱
│   ├── persistence/           # 会话持久化
│   ├── memory/                # 记忆系统
│   └── hitl/                  # 人机审批
├── tests/                      # 测试套件
├── docs/                       # 文档
│   ├── api/                   # API 参考
│   ├── architecture/          # 架构文档
│   ├── deployment/            # 部署指南
│   └── skills/                # 技能文档
├── docker-compose.yml          # 开发环境
├── docker-compose.prod.yml     # 生产环境
└── nginx.conf                  # Nginx 配置
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **8 个 Agent** | Coordinator, DataParser, DataProfiler, CodeGenerator, Debugger, Visualizer, ReportWriter, Chat |
| **13 个 Skill** | 内置分析技能 + 社区可扩展 |
| **代码自修复** | CodeGenerator → Debugger 最多 3 次重试 |
| **HITL 审批** | 3 级风险拦截 (INFO/CONFIRM/BLOCK) |
| **会话持久化** | PostgreSQL Checkpointer |
| **跨会话记忆** | 偏好/知识/模式积累 |
| **实时通信** | WebSocket + 指数退避重连 |

## 文档

- [API 参考](docs/api/REFERENCE.md)
- [部署指南](docs/deployment/DEPLOYMENT.md)
- [架构文档](docs/architecture/fullstack-progress.md)
- [技能系统](docs/skills/skills.md)

## License

MIT
