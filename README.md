# 🤖 自驱型多 Agent 自动化数据分析平台

基于 **LangGraph** 的生产级多智能体数据分析平台，支持用户通过自然语言完成数据上传、探索分析、代码生成、图表展示与报告输出。

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    用户界面 (Streamlit)                │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Coordinator (调度中心)                    │
│         意图识别 → 任务分类 → Agent 路由              │
└──┬───────┬────────┬─────────┬──────────┬────────────┘
   │       │        │         │          │
   ▼       ▼        ▼         ▼          ▼
 Data    Data    Code Gen  Visualizer  Report
 Parser  Profiler  erator              Writer
   │       │     ↓    ↑       │          │
   │       │   Debugger (自动修复循环)     │
   └───────┴────────┴─────────┴──────────┘
                    │
        ┌───────────▼───────────┐
        │   Skill Registry      │
        │  (能力注册 + 路由)     │
        ├───────────────────────┤
        │   Code Sandbox        │
        │  (subprocess 隔离执行) │
        └───────────────────────┘
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
| Agent 编排 | LangGraph StateGraph + langgraph-supervisor |
| LLM | DeepSeek V3 (via langchain-deepseek) |
| 状态管理 | 强类型 TypedDict + Annotated reducer |
| 数据处理 | pandas, numpy |
| 可视化 | matplotlib, plotly, seaborn |
| 前端 | Streamlit |
| 测试 | pytest |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
```

### 3. 运行测试

```bash
python -m pytest tests/ -v
```

### 4. 启动 Web 界面

```bash
streamlit run app.py
```

### 5. 命令行交互（可选）

```bash
python main.py
```

## 项目结构

```
multi-agent-data-analysis/
├── configs/
│   └── settings.py          # 全局配置管理
├── app.py                   # Streamlit Web 入口
├── src/
│   ├── agents/              # 8 个 Agent 实现
│   │   ├── coordinator.py   # 调度中心 (意图识别+路由)
│   │   ├── data_parser.py   # 数据解析专家
│   │   ├── data_profiler.py # 数据探索分析 (Skill 驱动)
│   │   ├── code_generator.py# LLM 动态代码生成
│   │   ├── debugger.py      # 自动修复 + 重试循环
│   │   ├── visualizer.py    # LLM 驱动可视化
│   │   ├── report_writer.py # Markdown 报告生成
│   │   └── chat.py          # 普通对话兆底
│   ├── graph/               # LangGraph 图定义
│   │   ├── state.py         # AnalysisState + DatasetMeta + CodeResult
│   │   └── builder.py       # StateGraph v3 (全 Agent + 双修复循环)
│   ├── skills/              # Skill 注册与管理
│   │   ├── base.py          # Skill/SkillMeta/SkillRegistry (SKILL.md 兼容)
│   │   ├── builtin_skills.py# 5 个内置分析 Skill
│   │   └── github_loader.py # GitHub Skill 下载器
│   ├── sandbox/             # 代码安全执行环境
│   │   └── executor.py      # subprocess 隔离 + 超时 + 安全检查
│   ├── persistence/         # 会话持久化
│   │   └── session_store.py # SQLite 存储会话/消息/数据集/产物
│   ├── memory/              # 跨会话记忆系统
│   │   └── memory_store.py  # 分析偏好 + 数据知识 + 操作模式
│   ├── hitl/                # Human-in-the-Loop 审批
│   │   └── approval.py      # 风险分析 + 审批管理器 + 3级拦截
│   └── utils/
│       ├── llm.py           # LLM 客户端封装
│       └── error_recovery.py# 重试 + 降级 + 异常处理
├── skills/                  # SKILL.md 格式技能
│   ├── community/           # 8 个社区 Skill (GitHub 下载)
│   └── examples/            # 示例 Skill
├── tests/                   # 测试套件 (116 tests)
│   ├── test_state.py        # 3 tests
│   ├── test_data_parser.py  # 10 tests
│   ├── test_graph_build.py  # 8 tests
│   ├── test_sandbox.py      # 13 tests
│   ├── test_skills.py       # 25 tests
│   ├── test_agents.py       # 7 tests
│   ├── test_visualizer.py   # 4 tests
│   ├── test_report_writer.py# 4 tests
│   ├── test_persistence.py  # 8 tests
│   ├── test_memory.py       # 10 tests
│   ├── test_hitl.py         # 11 tests
│   └── test_error_recovery.py# 13 tests
├── data/
│   └── sample/              # 示例数据
├── main.py                  # 命令行入口
├── requirements.txt
└── .env.example
```

## 开发路线

- [x] **阶段 1**: 项目骨架 — State 定义、Coordinator、DataParser、Graph 组装、16 tests
- [x] **阶段 2**: 核心 Agent + Skill 体系 + 代码沙箱 — DataProfiler、CodeGenerator、Debugger、SkillRegistry、Sandbox、49 tests
- [x] **阶段 3**: 可视化 + 报告 + 前端 — Streamlit UI、Visualizer、ReportWriter、8 个社区 Skill、73 tests
- [x] **阶段 4**: 生产化 — SQLite 持久化、HITL 审批、跨会话记忆、错误恢复、116 tests

### 阶段 4 新增能力

| 模块 | 说明 |
|------|------|
| **会话持久化** | SQLite 存储会话历史、消息、数据集元信息、代码/图表/报告产物，页面刷新不丢失 |
| **HITL 审批** | 3 级拦截（INFO/CONFIRM/BLOCK），代码风险自动分析，危险操作强制拦截，支持自动审批模式 |
| **记忆系统** | 跨会话知识积累（偏好/知识/模式），语义搜索，TTL 过期淮化，可注入 LLM 提示词 |
| **错误恢复** | 指数退避重试、优雅降级、全局异常捕获、用户友好错误消息转换 |

### 阶段 3 能力

| 模块 | 说明 |
|------|------|
| **Streamlit 前端** | ChatGPT 风格布局：左侧会话列表 + 文件上传，中间对话区，右侧代码/图表/报告面板 |
| **Visualizer Agent** | LLM 驱动智能可视化，自动选择图表类型，接入 Debugger 修复循环 |
| **ReportWriter Agent** | 汇总分析结果生成 Markdown 报告，可下载 |
| **社区 Skill** | 8 个 SKILL.md 格式 Skill（matplotlib/seaborn/plotly/scikit-learn/statsmodels/networkx等） |
| **StateGraph v3** | Visualizer + ReportWriter 替换占位，Visualizer 也接入 Debugger 自修复循环 |

### 阶段 2 能力

| 模块 | 说明 |
|------|------|
| **Code Sandbox** | subprocess 隔离执行，5s 超时熔断，危险代码拦截，自动图表捕获，Windows 兼容 |
| **Skill Registry** | 可注册/可版本化/可搜索，支持 SKILL.md 格式 + GitHub 加载 |
| **13 Skills** | 5 内置代码 Skill + 8 社区 SKILL.md Skill |
| **CodeGenerator Agent** | LLM 动态生成 pandas/matplotlib 代码，Sandbox 执行 |
| **Debugger Agent** | 捕获 stderr，LLM 自动修复代码，最多 3 次重试循环 |

## License

MIT
