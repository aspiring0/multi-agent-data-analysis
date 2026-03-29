"""
Chat Agent — 普通对话兜底
职责：当 Coordinator 判断用户不是在做数据分析时，用这个 Agent 回应。

同时也承担"占位"功能：
- 在后续阶段实现 data_profiler / code_generator / visualizer / report_writer 之前，
  这些未实现的 Agent 会先路由到此处，返回友好的"功能开发中"提示。
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

from src.graph.state import AnalysisState
from src.utils.llm import get_llm

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """你是一个友好的数据分析助手。
当前用户正在使用一个多 Agent 数据分析平台。
如果用户在闲聊，你可以正常回答。
如果用户提到了数据分析相关的需求，友好地引导他们上传数据文件。

回答要简洁、有帮助。使用中文回复。"""


def chat_node(state: AnalysisState) -> dict[str, Any]:
    """
    普通对话 Node

    读取：state["messages"]
    写入：state["messages"]（追加 AI 回复）
    """
    llm = get_llm()
    messages = state.get("messages", [])

    chat_messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]
    # 保留最近 10 条消息作为上下文
    recent = messages[-10:] if len(messages) > 10 else messages
    chat_messages.extend(recent)

    try:
        response = llm.invoke(chat_messages)
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"Chat Agent 调用失败: {e}")
        return {
            "messages": [AIMessage(content=f"抱歉，我遇到了一些问题: {str(e)}")],
            "error": str(e),
        }


def placeholder_node(agent_name: str):
    """
    占位 Node 工厂函数
    为尚未实现的 Agent 生成一个友好提示的 Node
    """

    def _node(state: AnalysisState) -> dict[str, Any]:
        return {
            "messages": [
                AIMessage(
                    content=f"🚧 `{agent_name}` 功能正在开发中...\n"
                    f"当前已支持：数据上传与解析、普通对话。\n"
                    f"更多分析能力即将上线！"
                )
            ]
        }

    _node.__name__ = agent_name
    return _node
