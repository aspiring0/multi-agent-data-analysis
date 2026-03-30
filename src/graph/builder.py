"""
Graph Builder — 核心图构建器 (v3)
将所有 Agent Node 组装成一个完整的 LangGraph StateGraph。

架构升级（阶段3）：
1. Visualizer Agent 替换占位（LLM 驱动可视化）
2. ReportWriter Agent 替换占位（Markdown 报告生成）
3. Visualizer 也接入 CodeGenerator→Debugger 自修复循环
4. 加载社区 Skill

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
 │       │    ↓       ↓    ↓       ↓      │          │
 │       │  debugger END  debugger END    │          │
 │       │    ↻                            │          │
 └───────┴────────────────────────────────┴──────────┘
                      │
                 ┌────▼────┐
                 │   END   │
                 └─────────┘
"""
from __future__ import annotations

import logging
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

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

# 加载社区 Skill（如果目录存在）
from src.skills.base import get_registry as _get_registry
_community_dir = Path(__file__).parent.parent.parent / "skills" / "community"
if _community_dir.exists():
    _get_registry().load_from_directory(_community_dir)

logger = logging.getLogger(__name__)


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
    graph.add_edge("data_profiler", END)
    graph.add_edge("report_writer", END)
    graph.add_edge("chat", END)

    # ============================================================
    # 4. 编译
    # ============================================================
    compile_kwargs = {"debug": debug}

    if with_checkpointer:
        compile_kwargs["checkpointer"] = InMemorySaver()

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
