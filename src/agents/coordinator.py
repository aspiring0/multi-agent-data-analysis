"""
Coordinator Agent — 调度中心
职责：
1. 理解用户意图
2. 判断任务类型（task_type）
3. 路由到对应的专业 Agent

设计原则：
- Coordinator 不执行任何业务逻辑，只做「理解 + 分发」
- 通过结构化输出（JSON）确保路由结果可解析
- 当无法判断意图时，回退到普通对话模式
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.graph.state import AnalysisState
from src.utils.llm import get_llm
from src.skills.base import get_registry

logger = logging.getLogger(__name__)

# ============================================================
# Coordinator 的系统提示词
# ============================================================
COORDINATOR_SYSTEM_PROMPT = """你是一个智能数据分析平台的调度中心（Coordinator）。

你的唯一职责是：分析用户的输入，判断用户意图，然后决定应该交给哪个专业 Agent 来处理。

## 可用的 Agent 及其职责

| Agent 名称 | 职责 | 触发场景 |
|------------|------|---------|
| data_parser | 数据解析与加载 | 用户上传了文件、要求加载数据、查看数据预览 |
| data_profiler | 数据探索与统计 | 用户要求查看数据概况、描述统计、缺失值分析、数据分布 |
| code_generator | 代码生成与执行 | 用户要求进行具体分析、数据清洗、特征工程、建模 |
| visualizer | 可视化生成 | 用户要求画图、生成图表、可视化展示 |
| report_writer | 报告生成 | 用户要求生成分析报告、总结分析结果 |
| chat | 普通对话 | 用户在闲聊、提问与数据分析无关的问题 |

## 输出格式

你必须严格输出以下 JSON 格式（不要输出其他任何内容）：

```json
{
    "intent": "用户意图的简要描述",
    "task_type": "上面表格中的任务类型之一: upload/parse/explore/visualize/clean/model/report/chat",
    "next_agent": "上面表格中的 Agent 名称之一",
    "reasoning": "你做出这个判断的理由（简要）"
}
```

## 当前已加载的数据集
{dataset_context}

## 可用分析技能（参考）
{skill_context}

## 注意事项
1. 如果用户消息中包含文件路径或提到上传文件，一定路由到 data_parser
2. 如果用户说"分析一下"但没指定具体方向，路由到 data_profiler 做整体概览
3. 如果用户提到"画图"“可视化”“图表”，路由到 visualizer
4. 如果用户提到"报告"“总结”，路由到 report_writer
5. 如果无法确定意图，默认路由到 chat
6. 只输出 JSON，不要有额外的解释文字
"""


def coordinator_node(state: AnalysisState) -> dict[str, Any]:
    """
    Coordinator Node：分析用户意图并路由到对应 Agent

    读取：state["messages"]（最后一条用户消息）
    写入：state["intent"], state["task_type"], state["next_agent"]
    """
    llm = get_llm()
    messages = state.get("messages", [])

    if not messages:
        return {
            "intent": "无输入",
            "task_type": "chat",
            "next_agent": "chat",
        }

    # 构建上下文
    datasets = state.get("datasets", [])
    dataset_context = "无已加载数据集"
    if datasets:
        ds_names = [f"{ds.get('file_name', '?')} ({ds.get('num_rows', '?')}行)" for ds in datasets]
        dataset_context = "\n".join(f"- {n}" for n in ds_names)

    registry = get_registry()
    skill_context = registry.get_skill_descriptions()[:500] if registry.count > 0 else "无"

    system_prompt = COORDINATOR_SYSTEM_PROMPT.format(
        dataset_context=dataset_context,
        skill_context=skill_context,
    )

    # 构建 Coordinator 专用的消息列表
    coordinator_messages = [
        SystemMessage(content=system_prompt),
    ]

    # 添加最近的对话上下文（最多保留最近 6 条）
    recent_messages = messages[-6:] if len(messages) > 6 else messages
    coordinator_messages.extend(recent_messages)

    # 调用 LLM
    try:
        response = llm.invoke(coordinator_messages)
        content = response.content.strip()

        # 解析 JSON 响应
        import re

        # 移除 DeepSeek <think> 标签
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # 提取 JSON 块（支持 ```json ``` 包裹）
        json_match = re.search(r"```(?:json)?\s*\n?(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        else:
            # 直接尝试找第一个 JSON 对象
            json_match = re.search(r"(\{[^{}]*\})", content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()

        result = json.loads(content)

        intent = result.get("intent", "未知意图")
        task_type = result.get("task_type", "chat")
        next_agent = result.get("next_agent", "chat")
        reasoning = result.get("reasoning", "")

        logger.info(
            f"Coordinator 路由决策: intent={intent}, "
            f"task_type={task_type}, next_agent={next_agent}, "
            f"reasoning={reasoning}"
        )

        return {
            "intent": intent,
            "task_type": task_type,
            "next_agent": next_agent,
        }

    except json.JSONDecodeError as e:
        logger.warning(f"Coordinator JSON 解析失败: {e}, 原始响应: {content}")
        return {
            "intent": "解析失败，回退到对话模式",
            "task_type": "chat",
            "next_agent": "chat",
        }
    except Exception as e:
        logger.error(f"Coordinator 调用失败: {e}")
        return {
            "intent": f"调度异常: {str(e)}",
            "task_type": "chat",
            "next_agent": "chat",
            "error": str(e),
        }


def route_by_agent(state: AnalysisState) -> str:
    """
    条件路由函数：根据 state["next_agent"] 决定下一个节点

    这个函数被 add_conditional_edges 使用。
    返回值必须与 Graph 中注册的 Node 名称一致。
    """
    next_agent = state.get("next_agent", "chat")

    # 验证 Agent 名称合法性
    valid_agents = {
        "data_parser", "data_profiler", "code_generator",
        "visualizer", "report_writer", "chat"
    }

    if next_agent not in valid_agents:
        logger.warning(f"未知的 Agent 名称: {next_agent}，回退到 chat")
        return "chat"

    return next_agent
