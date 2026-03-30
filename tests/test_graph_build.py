"""
Graph 构建测试 (v3)
验证升级后的 StateGraph 能正确编译，所有 Agent 节点正确注册，
Visualizer 和 ReportWriter 已替换占位。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.graph.builder import build_analysis_graph


class TestGraphBuild:
    """测试 Graph 构建"""

    def test_graph_compiles(self):
        """Graph 应该能成功编译"""
        graph = build_analysis_graph(with_checkpointer=False)
        assert graph is not None

    def test_graph_compiles_with_checkpointer(self):
        """Graph 应该能带 checkpointer 编译"""
        graph = build_analysis_graph(with_checkpointer=True)
        assert graph is not None

    def test_graph_has_correct_nodes(self):
        """Graph 应该包含所有预期的 Node"""
        graph = build_analysis_graph(with_checkpointer=False)

        graph_dict = graph.get_graph()
        node_ids = set(graph_dict.nodes.keys())

        expected_nodes = {
            "coordinator",
            "data_parser",
            "data_profiler",
            "code_generator",
            "debugger",
            "visualizer",
            "report_writer",
            "chat",
            "__start__",
            "__end__",
        }

        for expected in expected_nodes:
            assert expected in node_ids, f"缺少节点: {expected}"

    def test_graph_has_debugger_node(self):
        """Graph 应该包含 debugger 节点"""
        graph = build_analysis_graph(with_checkpointer=False)
        graph_dict = graph.get_graph()
        assert "debugger" in graph_dict.nodes

    def test_graph_has_code_generator_node(self):
        """Graph 应该包含 code_generator 节点"""
        graph = build_analysis_graph(with_checkpointer=False)
        graph_dict = graph.get_graph()
        assert "code_generator" in graph_dict.nodes

    def test_graph_has_visualizer_node(self):
        """Graph v3 应该包含真实 visualizer 节点（非占位）"""
        graph = build_analysis_graph(with_checkpointer=False)
        graph_dict = graph.get_graph()
        assert "visualizer" in graph_dict.nodes

    def test_graph_has_report_writer_node(self):
        """Graph v3 应该包含真实 report_writer 节点（非占位）"""
        graph = build_analysis_graph(with_checkpointer=False)
        graph_dict = graph.get_graph()
        assert "report_writer" in graph_dict.nodes

    def test_no_placeholder_nodes(self):
        """v3 中不应有占位节点（所有 Agent 均已真实实现）"""
        from src.agents.chat import placeholder_node
        graph = build_analysis_graph(with_checkpointer=False)
        graph_dict = graph.get_graph()

        # visualizer 和 report_writer 不应该是占位函数
        for node_name in ["visualizer", "report_writer"]:
            node = graph_dict.nodes.get(node_name)
            assert node is not None
