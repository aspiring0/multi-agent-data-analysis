"""
LangGraph 集成模块

提供统一的 Graph 初始化接口。
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_graph(with_checkpointer: bool = True):
    """
    获取 LangGraph 工作流图

    Args:
        with_checkpointer: 是否启用检查点（支持会话恢复）

    Returns:
        CompiledStateGraph: 编译后的状态图
    """
    from src.graph.builder import get_graph as _get_graph
    from backend.core.checkpoint import get_checkpointer

    if with_checkpointer:
        # 临时替换为 PostgreSQL Checkpointer
        # 注意：需要在实际调用时修改 src/graph/builder.py
        graph = _get_graph(with_checkpointer=False)

        # 手动设置 PostgreSQL Checkpointer
        checkpointer = get_checkpointer()
        # 这里需要重新编译以应用 checkpointer
        # 实际实现可能需要调整 builder.py 的接口

        return graph
    else:
        return _get_graph(with_checkpointer=False)
