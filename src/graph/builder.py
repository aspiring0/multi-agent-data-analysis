"""
Graph Builder — 核心图构建器 (v4)
将所有 Agent Node 组装成一个完整的 LangGraph StateGraph。

架构升级（阶段4）：
1. DataProfiler 失败时也触发 Debugger 修复
2. 所有代码执行节点都接入自修复循环
3. 更健壮的错误恢复机制

Graph 结构：

    ┌─────────┐
    │  START   │
    └────┬─────┘
         │
    ┌────▼──────────┐
    │  coordinator  │  ← 意图识别 + 路由
    └────┬──────────┘
         │ (conditional_edges)
         │
 ┌───────┼────────┬───────────┬───────────┬──────────┐
 │       │        │           │           │          │
 ▼       ▼        ▼           ▼           ▼          ▼
data   data    code_gen   visualizer  report     chat
parser profiler  │             │        writer
 │       │    should_retry  should_retry  │          │
 │       │    ┌───┴───┐    ┌───┴───┐      │          │
 │       │  retry   done retry   done     │          │
 │    should_retry  ↓    ↓       ↓        │          │
 │    ┌───┴───┐  debugger END             │          │
 │  retry   done                          │          │
 │    ↓       ↓                           │          │
 │  debugger END                          │          │
 │    ↻                                    │          │
 └─────────────────────────────────────────┴──────────┘
                      │
                 ┌────▼────┐
                 │   END   │
                 └─────────┘
"""
from __future__ import annotations

import logging
from pathlib import Path

from langgraph.graph import StateGraph, END

from src.graph.state import AnalysisState
from src.agents.coordinator import coordinator_node, route_by_agent
from src.agents.data_parser import data_parser_node
from src.agents.data_profiler import data_profiler_node
from src.agents.code_generator import code_generator_node
from src.agents.debugger import debugger_node, should_retry
from src.agents.visualizer import visualizer_node
from src.agents.report_writer import report_writer_node
from src.agents.chat import chat_node

# 确保内置 Skill 已注册
from src.skills.builtin_skills import register_builtin_skills as _register
_register()

# 加载示例 Skill（如果目录存在）
from src.skills.base import get_registry as _get_registry
_examples_dir = Path(__file__).parent.parent.parent / "skills" / "examples"
if _examples_dir.exists():
    _get_registry().load_from_directory(_examples_dir)

logger = logging.getLogger(__name__)


def _get_checkpointer():
    """获取 Checkpointer（根据 CHECKPOINTER_TYPE 配置选择）"""
    from configs.settings import settings
    from langgraph.checkpoint.memory import InMemorySaver

    checkpointer_type = settings.CHECKPOINTER_TYPE.lower()

    if checkpointer_type == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            logger.info(f"使用 PostgreSQL Checkpointer")
            return PostgresSaver.from_conn_string(settings.POSTGRES_URI)
        except Exception as e:
            logger.warning(f"PostgreSQL 连接失败，降级到内存存储: {e}")
            return InMemorySaver()
    else:
        logger.info("使用内存 Checkpointer")
        return InMemorySaver()


def build_analysis_graph(
    with_checkpointer: bool = True,
    debug: bool = False,
) -> "CompiledStateGraph":
    """
    构建并编译数据分析工作流图 (v3)

    Args:
        with_checkpointer: 是否启用内存检查点（支持会话恢复）
        debug: 是否开启调试模式

    Returns:
        编译后的 StateGraph
    """
    # ============================================================
    # 1. 创建 StateGraph
    # ============================================================
    graph = StateGraph(AnalysisState)

    # ============================================================
    # 2. 注册所有 Node
    # ============================================================

    # 调度中心（入口）
    graph.add_node("coordinator", coordinator_node)

    # 数据层
    graph.add_node("data_parser", data_parser_node)
    graph.add_node("data_profiler", data_profiler_node)

    # 代码生成 + 修复循环
    graph.add_node("code_generator", code_generator_node)
    graph.add_node("debugger", debugger_node)

    # 可视化（阶段3 — 真实实现）
    graph.add_node("visualizer", visualizer_node)

    # 报告（阶段3 — 真实实现）
    graph.add_node("report_writer", report_writer_node)

    # 对话兜底
    graph.add_node("chat", chat_node)

    # ============================================================
    # 3. 定义边 (Edges)
    # ============================================================

    # START → coordinator
    graph.set_entry_point("coordinator")

    # coordinator → (条件路由) → 各个 Agent
    graph.add_conditional_edges(
        "coordinator",
        route_by_agent,
        {
            "data_parser": "data_parser",
            "data_profiler": "data_profiler",
            "code_generator": "code_generator",
            "visualizer": "visualizer",
            "report_writer": "report_writer",
            "chat": "chat",
        },
    )

    # === CodeGenerator → Debugger 自修复循环 ===
    graph.add_conditional_edges(
        "code_generator",
        should_retry,
        {
            "retry": "debugger",
            "done": END,
        },
    )

    # === Visualizer → Debugger 自修复循环 ===
    # Visualizer 也可能生成失败的代码，复用 Debugger 修复
    graph.add_conditional_edges(
        "visualizer",
        should_retry,
        {
            "retry": "debugger",
            "done": END,
        },
    )

    # Debugger 自循环
    graph.add_conditional_edges(
        "debugger",
        should_retry,
        {
            "retry": "debugger",
            "done": END,
        },
    )

    # 其他 Agent → END（单次执行）
    graph.add_edge("data_parser", END)

    # === DataProfiler → Debugger 自修复循环（新增）===
    # DataProfiler 执行 Skill 失败时也触发修复
    graph.add_conditional_edges(
        "data_profiler",
        should_retry,
        {
            "retry": "debugger",
            "done": END,
        },
    )

    graph.add_edge("report_writer", END)
    graph.add_edge("chat", END)

    # ============================================================
    # 4. 编译
    # ============================================================
    compile_kwargs = {"debug": debug}

    if with_checkpointer:
        compile_kwargs["checkpointer"] = _get_checkpointer()

    compiled = graph.compile(**compile_kwargs)
    logger.info("数据分析工作流图 v3 编译完成（Visualizer + ReportWriter 已接入）")

    return compiled


# ============================================================
# 便捷接口
# ============================================================
_graph_instance = None


def get_graph(force_rebuild: bool = False, **kwargs) -> "CompiledStateGraph":
    """获取或构建全局 Graph 实例"""
    global _graph_instance
    if _graph_instance is None or force_rebuild:
        _graph_instance = build_analysis_graph(**kwargs)
    return _graph_instance


# ============================================================
# V2: 多轮调度工作流图
# ============================================================

def build_analysis_graph_v2(
    with_checkpointer: bool = True,
    debug: bool = False,
) -> "CompiledStateGraph":
    """
    构建多轮调度数据分析工作流图 (V2)

    与 V1 的区别：
    - Coordinator 作为统一调度中心
    - Agent 执行后返回 Coordinator（而不是 END）
    - Coordinator 根据任务队列决定下一步

    Graph 结构：

        START → coordinator_v2
                    │
         ┌──────────┼──────────┬──────────┬──────────┐
         │          │          │          │          │
         ▼          ▼          ▼          ▼          ▼
     data_profiler code_gen  visualizer  report    chat
         │          │          │          │          │
         └────┬─────┴────┬─────┴────┬─────┘          │
              │          │          │                │
              ▼          ▼          ▼                ▼
              └──────────┴──────────┴────────────────┘
                              │
                         coordinator_v2
                              │
                         ┌────┴────┐
                    队列为空?    队列不为空
                         │           │
                        END      继续执行
    """
    from langgraph.graph import StateGraph, END
    from src.graph.state import AnalysisState
    from src.agents.coordinator_v2 import coordinator_v2_node, route_by_agent_v2

    # 创建 StateGraph
    graph = StateGraph(AnalysisState)

    # ============================================================
    # 1. 注册所有 Node
    # ============================================================

    # 调度中心（入口）
    graph.add_node("coordinator_v2", coordinator_v2_node)

    # 专业 Agent
    graph.add_node("data_profiler", data_profiler_node)
    graph.add_node("code_generator", code_generator_node)
    graph.add_node("visualizer", visualizer_node)
    graph.add_node("report_writer", report_writer_node)
    graph.add_node("chat", chat_node)
    graph.add_node("debugger", debugger_node)

    # ============================================================
    # 2. 定义边
    # ============================================================

    # START → coordinator_v2
    graph.set_entry_point("coordinator_v2")

    # coordinator_v2 → 条件路由到各个 Agent
    graph.add_conditional_edges(
        "coordinator_v2",
        route_by_agent_v2,
        {
            "data_profiler": "data_profiler",
            "code_generator": "code_generator",
            "visualizer": "visualizer",
            "report_writer": "report_writer",
            "chat": "chat",
            END: END,
        },
    )

    # 所有 Agent 执行后返回 coordinator_v2（支持多轮调度）
    # 但如果有错误需要修复，先去 debugger

    # code_generator 失败时去 debugger，成功时返回 coordinator
    graph.add_conditional_edges(
        "code_generator",
        should_retry,
        {
            "retry": "debugger",
            "done": "coordinator_v2",
        },
    )

    # visualizer 同样
    graph.add_conditional_edges(
        "visualizer",
        should_retry,
        {
            "retry": "debugger",
            "done": "coordinator_v2",
        },
    )

    # data_profiler 同样
    graph.add_conditional_edges(
        "data_profiler",
        should_retry,
        {
            "retry": "debugger",
            "done": "coordinator_v2",
        },
    )

    # debugger 修复后返回 coordinator
    graph.add_conditional_edges(
        "debugger",
        should_retry,
        {
            "retry": "debugger",
            "done": "coordinator_v2",
        },
    )

    # report_writer 和 chat 直接返回 coordinator
    graph.add_edge("report_writer", "coordinator_v2")
    graph.add_edge("chat", "coordinator_v2")

    # ============================================================
    # 3. 编译
    # ============================================================
    compile_kwargs = {"debug": debug}

    if with_checkpointer:
        compile_kwargs["checkpointer"] = _get_checkpointer()

    compiled = graph.compile(**compile_kwargs)
    logger.info("数据分析工作流图 V2 编译完成（多轮调度支持）")

    return compiled


# V2 实例缓存
_graph_v2_instance = None


def get_graph_v2(force_rebuild: bool = False, **kwargs) -> "CompiledStateGraph":
    """获取或构建全局 Graph V2 实例（多轮调度）"""
    global _graph_v2_instance
    if _graph_v2_instance is None or force_rebuild:
        _graph_v2_instance = build_analysis_graph_v2(**kwargs)
    return _graph_v2_instance
