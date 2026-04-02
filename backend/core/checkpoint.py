"""
PostgreSQL Checkpointer 配置

为 LangGraph 提供持久化的检查点存储，支持会话恢复。
"""
import os
from langgraph.checkpoint.postgres import PostgresSaver

# 从环境变量读取数据库连接
POSTGRES_URI = os.getenv(
    "POSTGRES_URI",
    "postgresql://postgres:postgres@localhost:5432/langgraph"
)


def get_checkpointer():
    """
    获取 PostgreSQL Checkpointer

    Returns:
        PostgresSaver: LangGraph 检查点存储器
    """
    return PostgresSaver.from_conn_string(POSTGRES_URI)


_checkpointer_instance = None


def get_checkpointer_singleton():
    """
    获取单例 Checkpointer

    Returns:
        PostgresSaver: 全局唯一的 Checkpointer 实例
    """
    global _checkpointer_instance
    if _checkpointer_instance is None:
        _checkpointer_instance = get_checkpointer()
    return _checkpointer_instance
