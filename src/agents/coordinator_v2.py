"""
Coordinator Agent V2 - 意图识别与路由协调器
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage

from src.agents.base import BaseAgent, AgentContext, register_agent

logger = logging.getLogger(__name__)

# 意图关键词映射
INTENT_KEYWORDS = {
    "DATA_LOAD": ["load", "parse", "upload", "读取", "加载", "导入", "open"],
    "DATA_ANALYSIS": ["analyze", "profile", "explore", "分析", "探索", "概览", "统计", "排名", "比较"],
    "CODE_GEN": ["generate", "create", "code", "生成", "代码", "写"],
    "DEBUG": ["fix", "debug", "error", "修复", "调试", "报错", "错误"],
    "VISUALIZE": ["plot", "chart", "visualize", "画图", "图表", "可视化", "展示"],
    "ML_PREDICTION": ["predict", "model", "forecast", "预测", "建模", "训练"],
}

# 意图到 Agent 的路由表
INTENT_TO_AGENT = {
    "DATA_LOAD": "data_parser",
    "DATA_ANALYSIS": "data_profiler",
    "CODE_GEN": "code_generator",
    "DEBUG": "debugger",
    "VISUALIZE": "visualizer",
    "ML_PREDICTION": "planner",  # 复杂任务交给 Planner
    "UNKNOWN": "data_profiler",  # 默认
}


@dataclass
class Intent:
    """意图分类结果"""
    category: str
    confidence: float
    keywords_matched: list[str]


@register_agent
class CoordinatorAgent(BaseAgent):
    """
    协调器 Agent

    从 AGENT.md 加载定义，负责意图识别和路由。
    """

    name = "coordinator"

    async def run(self, context: AgentContext) -> dict[str, Any]:
        """
        执行协调逻辑

        工作流:
        1. 从消息中识别意图
        2. 根据意图选择目标 Agent
        3. 更新状态并返回路由信息
        """
        state = context.state
        messages = state.get("messages", [])

        # 获取最近的用户消息
        user_message = self._get_latest_user_message(messages)
        if not user_message:
            return {
                "messages": [AIMessage(content="请告诉我您想做什么？")],
                "next_agent": "data_profiler",
            }

        # 识别意图
        intent = self._classify_intent(user_message)

        # 选择目标 Agent
        next_agent = self._select_agent(intent, state)

        # 更新路由历史
        route_history = list(state.get("route_history", []))
        route_history.append("coordinator")

        logger.info(f"Intent: {intent.category} -> Agent: {next_agent}")

        return {
            "intent": intent.category,
            "intent_confidence": intent.confidence,
            "next_agent": next_agent,
            "route_history": route_history,
        }

    def _get_latest_user_message(self, messages: list) -> str:
        """获取最近的用户消息"""
        from langchain_core.messages import HumanMessage

        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
            if hasattr(msg, "type") and msg.type == "human":
                return msg.content
        return ""

    def _classify_intent(self, message: str) -> Intent:
        """分类意图"""
        message_lower = message.lower()

        # 计算每个类别的匹配分数
        scores = {}
        for category, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[category] = score

        if not scores:
            return Intent(category="UNKNOWN", confidence=0.0, keywords_matched=[])

        # 选择最高分
        best_category = max(scores, key=scores.get)
        total_keywords = len(INTENT_KEYWORDS[best_category])
        confidence = min(scores[best_category] / max(total_keywords, 1) * 2, 1.0)

        matched = [kw for kw in INTENT_KEYWORDS[best_category] if kw in message_lower]

        return Intent(
            category=best_category,
            confidence=confidence,
            keywords_matched=matched,
        )

    def _select_agent(self, intent: Intent, state: dict) -> str:
        """根据意图和状态选择 Agent"""
        # 数据未加载 → 先加载
        datasets = state.get("datasets", [])
        if not datasets and intent.category != "DATA_LOAD":
            logger.info("No datasets loaded, routing to data_parser first")
            return "data_parser"

        return INTENT_TO_AGENT.get(intent.category, "data_profiler")


# 兼容性别名
Coordinator = CoordinatorAgent