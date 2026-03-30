"""
Graph Builder — 核心图构建器 (v2)
将所有 Agent Node 组装成一个完整的 LangGraph StateGraph。

架构升级（阶段2）：
1. 新增 DataProfiler、CodeGenerator、Debugger Agent
2. CodeGenerator → Debugger 形成自修复循环
3. 占位 Agent 替换为真实实现
4. 保留 visualizer 和 report_writer 占位

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
data   data    code_gen → debugger  visual    report  chat
parser profiler  ↻ (循环)     izer     writer
 │       │        │           │           │          │
 └───────┴────────┴───────────┴───────────┴──────────┘
                          │
                     ┌────▼────┐
                     │   END   │
                     └─────────┘
"""
from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from src.graph.state import AnalysisState
from src.agents.coordinator import coordinator_node, route_by_agent
from src.agents.data_parser import data_parser_node
from src.agents.data_profiler import data_profiler_node
from src.agents.code_generator import code_generator_node
from src.agents.debugger import debugger_node, should_retry
from src.agents.chat import chat_node, placeholder_node

# 确保内置 Skill 已注册
from src.skills.builtin_skills import register_builtin_skills as _register
_register()

logger = logging.getLogger(__name__)


def build_analysis_graph(
    with_checkpointer: bool = True,
    debug: bool = False,
) -> "CompiledStateGraph":
    """
    构建并编译数据分析工作流图 (v2)

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

    # 已实现的 Agent
    graph.add_node("data_parser", data_parser_node)
    graph.add_node("data_profiler", data_profiler_node)
    graph.add_node("code_generator", code_generator_node)
    graph.add_node("debugger", debugger_node)
    graph.add_node("chat", chat_node)

    # 占位 Agent（阶段3实现）
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

    # === CodeGenerator → Debugger 自修复循环 ===
    # code_generator 执行完后，检查是否需要修复
    graph.add_conditional_edges(
        "code_generator",
        should_retry,
        {
            "retry": "debugger",   # 执行失败 → 修复
            "done": END,           # 执行成功 → 结束
        },
    )

    # debugger 执行完后，再检查是否需要继续修复
    graph.add_conditional_edges(
        "debugger",
        should_retry,
        {
            "retry": "debugger",   # 继续修复（自循环）
            "done": END,           # 修复成功或超限 → 结束
        },
    )

    # 其他 Agent → END（单次执行）
    graph.add_edge("data_parser", END)
    graph.add_edge("data_profiler", END)
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
    logger.info("数据分析工作流图 v2 编译完成（含 CodeGenerator → Debugger 循环）")

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
