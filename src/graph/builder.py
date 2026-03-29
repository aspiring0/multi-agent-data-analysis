"""
Graph Builder — 核心图构建器
将所有 Agent Node 组装成一个完整的 LangGraph StateGraph。

架构：
    START → coordinator → (条件路由) → data_parser / data_profiler / ... / chat → END

设计原则：
1. Coordinator 是唯一入口，所有请求先经过意图识别
2. 条件路由基于 state["next_agent"] 分发到专业 Agent
3. 每个专业 Agent 执行完毕后直接进入 END（单轮执行）
4. 后续迭代可以加入循环（如 code_generator → debugger → code_generator）
"""
from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from src.graph.state import AnalysisState
from src.agents.coordinator import coordinator_node, route_by_agent
from src.agents.data_parser import data_parser_node
from src.agents.chat import chat_node, placeholder_node

logger = logging.getLogger(__name__)


def build_analysis_graph(
    with_checkpointer: bool = True,
    debug: bool = False,
) -> "CompiledStateGraph":
    """
    构建并编译数据分析工作流图

    Args:
        with_checkpointer: 是否启用内存检查点（支持会话恢复）
        debug: 是否开启调试模式

    Returns:
        编译后的 StateGraph，可直接 invoke 或 stream

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
     ┌───────┼────────┬──────────┬──────────┬──────────┐
     │       │        │          │          │          │
     ▼       ▼        ▼          ▼          ▼          ▼
   data    data    code_gen   visual    report      chat
   parser  profiler  ator      izer     writer
     │       │        │          │          │          │
     └───────┴────────┴──────────┴──────────┴──────────┘
                              │
                         ┌────▼────┐
                         │   END   │
                         └─────────┘
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

    # 已实现的 Agent
    graph.add_node("data_parser", data_parser_node)
    graph.add_node("chat", chat_node)

    # 占位 Agent（后续阶段实现）
    graph.add_node("data_profiler", placeholder_node("data_profiler"))
    graph.add_node("code_generator", placeholder_node("code_generator"))
    graph.add_node("visualizer", placeholder_node("visualizer"))
    graph.add_node("report_writer", placeholder_node("report_writer"))

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

    # 所有 Agent → END
    graph.add_edge("data_parser", END)
    graph.add_edge("data_profiler", END)
    graph.add_edge("code_generator", END)
    graph.add_edge("visualizer", END)
    graph.add_edge("report_writer", END)
    graph.add_edge("chat", END)

    # ============================================================
    # 4. 编译
    # ============================================================
    compile_kwargs = {"debug": debug}

    if with_checkpointer:
        compile_kwargs["checkpointer"] = InMemorySaver()

    compiled = graph.compile(**compile_kwargs)
    logger.info("数据分析工作流图编译完成")

    return compiled


# ============================================================
# 便捷接口：获取全局 Graph 实例
# ============================================================
_graph_instance = None


def get_graph(force_rebuild: bool = False, **kwargs) -> "CompiledStateGraph":
    """获取或构建全局 Graph 实例"""
    global _graph_instance
    if _graph_instance is None or force_rebuild:
        _graph_instance = build_analysis_graph(**kwargs)
    return _graph_instance
