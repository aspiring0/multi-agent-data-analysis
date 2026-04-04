"""
Coordinator Agent V2 - 统一调度中心

职责：
1. 分析用户意图，拆解成多个子任务
2. 按顺序分配给合适的 Agent
3. 收集结果，决定是否需要更多 Agent 参与
4. 汇总最终结果返回给用户

设计原则：
- Coordinator 是调度中心，不是简单的路由器
- 支持多轮调度，Agent 执行后返回 Coordinator
- 每个任务有明确的 ID 和状态跟踪
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END

from src.graph.state import AnalysisState, TaskItem
from src.utils.llm import get_llm
from src.skills.base import get_registry

logger = logging.getLogger(__name__)

# ============================================================
# Coordinator V2 的系统提示词
# ============================================================
COORDINATOR_V2_SYSTEM_PROMPT = """你是一个智能数据分析平台的**调度中心（Coordinator）**。

你的职责是：分析用户需求，**拆解成多个子任务**，然后按顺序分配给合适的专业 Agent。

## 可用的 Agent 及其职责

| Agent 名称 | 职责 | 触发场景 |
|------------|------|---------|
| data_profiler | 数据探索与统计 | 用户要求查看整体数据概况、描述统计、缺失值分析 |
| code_generator | 代码生成与执行 | 用户要求具体分析（占比、趋势、对比、筛选、计算等） |
| visualizer | 可视化生成 | 用户要求画图、生成图表、可视化展示 |
| report_writer | 报告生成 | 用户要求生成分析报告、总结分析结果 |
| chat | 普通对话 | 用户在闲聊、提问与数据分析无关的问题 |

## 任务拆解原则

1. **一次请求可能需要多个 Agent 协作**
   - 例："分析销售趋势并画图" → [code_generator, visualizer]
   - 例："看看数据概况" → [data_profiler]
   - 例："计算每个地区的销售占比" → [code_generator]

2. **任务顺序很重要**
   - 先探索数据，再进行分析
   - 先分析完成，再生成可视化
   - 最后生成报告

3. **避免过度拆分**
   - 简单请求不需要拆分
   - 只有明确需要多种分析时才拆分

## 输出格式

你必须严格输出以下 JSON 格式（不要输出其他任何内容）：

```json
{{
    "intent": "用户意图的简要描述",
    "tasks": [
        {{
            "agent": "Agent名称",
            "description": "这个任务要做什么"
        }}
    ],
    "reasoning": "你做出这个判断的理由（简要）"
}}
```

## 当前已加载的数据集
{dataset_context}

## 注意事项
1. 如果用户只是闲聊或提问与数据分析无关的问题，tasks 只包含 chat
2. 如果没有数据集但用户要求分析，tasks 只包含 chat，并让 chat 告诉用户上传数据
3. 只输出 JSON，不要有额外的解释文字
"""


def coordinator_v2_node(state: AnalysisState) -> dict[str, Any]:
    """
    Coordinator V2 Node：统一调度中心

    工作流程：
    1. 如果任务队列为空，分析用户消息并拆解任务
    2. 如果有新消息但任务队列不为空，说明是 Agent 返回的结果，记录并取下一个任务
    3. 如果任务队列不为空，取下一个任务执行
    4. 如果所有任务完成，生成汇总回复

    读取：state["messages"], state["task_queue"], state["completed_tasks"]
    写入：state["task_queue"], state["current_task"], state["next_agent"], state["scheduling_complete"]
    """
    messages = state.get("messages", [])
    task_queue = state.get("task_queue", [])
    completed_tasks = state.get("completed_tasks", [])

    # 情况 1: 任务队列为空，需要分析用户消息
    if not task_queue and not completed_tasks:
        return _analyze_and_plan(state)

    # 情况 2: 刚完成一个任务，检查是否还有更多任务
    if not task_queue and completed_tasks:
        # 所有任务完成，生成汇总回复
        return _summarize_results(state)

    # 情况 3: 任务队列不为空，取下一个任务执行
    if task_queue:
        next_task = task_queue[0]
        remaining_tasks = task_queue[1:]

        logger.info(f"Coordinator 分配任务: {next_task['agent']} - {next_task['description']}")

        return {
            "current_task": next_task,
            "task_queue": remaining_tasks,
            "next_agent": next_task["agent"],
        }

    # 不会到达这里
    return {"next_agent": "chat"}


def _analyze_and_plan(state: AnalysisState) -> dict[str, Any]:
    """分析用户消息并规划任务"""
    llm = get_llm()
    messages = state.get("messages", [])

    if not messages:
        return {
            "intent": "无输入",
            "next_agent": "chat",
            "task_queue": [],
            "scheduling_complete": True,
        }

    # 构建上下文
    datasets = state.get("datasets", [])
    dataset_context = "无已加载数据集"
    if datasets:
        ds_names = [f"{ds.get('file_name', '?')} ({ds.get('num_rows', '?')}行)" for ds in datasets]
        dataset_context = "\n".join(f"- {n}" for n in ds_names)

    system_prompt = COORDINATOR_V2_SYSTEM_PROMPT.format(
        dataset_context=dataset_context,
    )

    # 构建消息列表
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

        # 移除 DeepSeek <think/> 标签
        content = re.sub(r"<think/>.*?</think/>", "", content, flags=re.DOTALL).strip()

        # 提取 JSON 块
        json_match = re.search(r"```(?:json)?\s*\n?(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        else:
            json_match = re.search(r"(\{[^{}]*\})", content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()

        result = json.loads(content)

        intent = result.get("intent", "未知意图")
        tasks = result.get("tasks", [])
        reasoning = result.get("reasoning", "")

        # 转换任务为 TaskItem 格式
        task_items = []
        for i, task in enumerate(tasks):
            task_item: TaskItem = {
                "id": str(uuid.uuid4())[:8],
                "agent": task.get("agent", "chat"),
                "description": task.get("description", ""),
                "status": "pending",
                "result_summary": "",
            }
            task_items.append(task_item)

        logger.info(
            f"Coordinator V2 规划: intent={intent}, "
            f"tasks={[t['agent'] for t in task_items]}, "
            f"reasoning={reasoning}"
        )

        # 如果没有任务，默认到 chat
        if not task_items:
            task_items = [{"id": "default", "agent": "chat", "description": "默认对话", "status": "pending", "result_summary": ""}]

        # 取第一个任务执行
        first_task = task_items[0]
        remaining_tasks = task_items[1:]

        return {
            "intent": intent,
            "task_queue": remaining_tasks,
            "current_task": first_task,
            "next_agent": first_task["agent"],
            "completed_tasks": [],
            "scheduling_complete": False,
        }

    except json.JSONDecodeError as e:
        logger.warning(f"Coordinator V2 JSON 解析失败: {e}, 原始响应: {content}")
        return {
            "intent": "解析失败，回退到对话模式",
            "task_queue": [],
            "next_agent": "chat",
            "scheduling_complete": True,
        }
    except Exception as e:
        logger.error(f"Coordinator V2 调用失败: {e}")
        return {
            "intent": f"调度异常: {str(e)}",
            "task_queue": [],
            "next_agent": "chat",
            "error": str(e),
            "scheduling_complete": True,
        }


def _summarize_results(state: AnalysisState) -> dict[str, Any]:
    """所有任务完成，生成汇总回复"""
    completed_tasks = state.get("completed_tasks", [])
    messages = state.get("messages", [])

    # 构建汇总
    summary_parts = []
    for task in completed_tasks:
        agent = task.get("agent", "unknown")
        result = task.get("result_summary", "")
        if result:
            summary_parts.append(f"- **{agent}**: {result[:100]}...")

    if summary_parts:
        summary = f"## ✅ 分析完成\n\n已执行 {len(completed_tasks)} 个任务:\n" + "\n".join(summary_parts)
    else:
        summary = "✅ 分析完成"

    return {
        "messages": [AIMessage(content=summary)],
        "scheduling_complete": True,
        "next_agent": END,
    }


def route_by_agent_v2(state: AnalysisState) -> str:
    """
    条件路由函数 V2：根据 state["next_agent"] 决定下一个节点

    与 V1 不同：
    - 如果 scheduling_complete 为 True，返回 END
    - 否则正常路由
    """
    # 检查是否调度完成
    if state.get("scheduling_complete", False):
        return END

    next_agent = state.get("next_agent", "chat")

    # 验证 Agent 名称合法性
    valid_agents = {
        "data_profiler", "code_generator", "visualizer",
        "report_writer", "chat"
    }

    if next_agent == END:
        return END

    if next_agent not in valid_agents:
        logger.warning(f"未知的 Agent 名称: {next_agent}，回退到 chat")
        return "chat"

    return next_agent


def mark_task_complete(state: AnalysisState, result_summary: str = "") -> dict[str, Any]:
    """
    标记当前任务完成，将结果添加到已完成列表

    由各个 Agent 在完成工作后调用
    """
    current_task = state.get("current_task")
    completed_tasks = list(state.get("completed_tasks", []))

    if current_task:
        completed_task = dict(current_task)
        completed_task["status"] = "completed"
        completed_task["result_summary"] = result_summary
        completed_tasks.append(completed_task)

    return {"completed_tasks": completed_tasks}