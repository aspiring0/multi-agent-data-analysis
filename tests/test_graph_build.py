"""
Graph 构建测试
验证 StateGraph 能正确编译，节点和边都正确注册。
这些测试不需要 LLM API。
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
        """Graph 应该能成功编译（不启用 checkpointer）"""
        graph = build_analysis_graph(with_checkpointer=False)
        assert graph is not None

    def test_graph_compiles_with_checkpointer(self):
        """Graph 应该能带 checkpointer 编译"""
        graph = build_analysis_graph(with_checkpointer=True)
        assert graph is not None

    def test_graph_has_correct_nodes(self):
        """Graph 应该包含所有预期的 Node"""
        graph = build_analysis_graph(with_checkpointer=False)

        # 获取图的节点信息
        graph_dict = graph.get_graph()
        node_ids = set(graph_dict.nodes.keys())

        expected_nodes = {
            "coordinator",
            "data_parser",
            "data_profiler",
            "code_generator",
            "visualizer",
            "report_writer",
            "chat",
            "__start__",
            "__end__",
        }

        for expected in expected_nodes:
            assert expected in node_ids, f"缺少节点: {expected}"
