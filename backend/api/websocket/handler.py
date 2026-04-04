"""
WebSocket 处理器

处理实时聊天通信和流式响应。
支持 V1 (单次路由) 和 V2 (多轮调度) 两种模式。
"""
import logging
from pathlib import Path
from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

from src.graph.builder import get_graph, get_graph_v2
from src.persistence.session_store import SessionStore
from configs.settings import settings

logger = logging.getLogger(__name__)

# 是否使用 V2 多轮调度模式
USE_GRAPH_V2 = getattr(settings, 'USE_GRAPH_V2', True)


async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 聊天处理器

    Args:
        websocket: WebSocket 连接
        session_id: 会话 ID
    """
    await websocket.accept()
    logger.info(f"WebSocket 连接建立: session_id={session_id}")

    try:
        # 发送连接确认
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id
        })

        while True:
            # 接收消息
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "ping":
                # 心跳检测
                await websocket.send_json({"type": "pong"})
                continue

            if message_type == "message":
                # 用户消息
                user_message = data.get("message")
                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "消息内容不能为空"
                    })
                    continue

                # 保存用户消息到数据库
                store = SessionStore()
                session = store.get_session(session_id)
                if not session:
                    # 会话不存在，自动创建
                    store.create_session(session_id, f"会话 {session_id[:6]}")
                    logger.info(f"自动创建会话: {session_id}")

                store.add_message(session_id, "user", user_message)

                # 获取 Graph（V2 支持多轮调度）
                if USE_GRAPH_V2:
                    graph = get_graph_v2(with_checkpointer=False)
                    logger.debug("使用 V2 多轮调度 Graph")
                else:
                    graph = get_graph(with_checkpointer=False)
                    logger.debug("使用 V1 单次路由 Graph")

                # 构建状态
                state = {
                    "session_id": session_id,  # 传递 session_id 用于数据获取
                    "messages": [HumanMessage(content=user_message)],
                    "datasets": store.get_datasets(session_id),
                    "active_dataset_index": 0,
                    # V2 调度状态
                    "task_queue": [],
                    "completed_tasks": [],
                    "scheduling_complete": False,
                }

                # 发送开始标记
                await websocket.send_json({"type": "start"})

                # 流式处理
                try:
                    accumulated_state = {}

                    async for chunk in graph.astream(
                        state,
                        config={"configurable": {"thread_id": session_id}}
                    ):
                        for node_name, node_output in chunk.items():
                            # 发送 Agent 执行状态
                            agent_names = {
                                "coordinator": "调度中心",
                                "coordinator_v2": "调度中心 V2",
                                "data_parser": "数据解析",
                                "data_profiler": "数据探索",
                                "code_generator": "代码生成",
                                "debugger": "代码修复",
                                "visualizer": "可视化",
                                "report_writer": "报告生成",
                                "chat": "对话"
                            }
                            agent_display = agent_names.get(node_name, node_name)

                            # 发送任务队列状态（V2 模式）
                            if "task_queue" in node_output or "completed_tasks" in node_output:
                                task_queue = node_output.get("task_queue", [])
                                completed = node_output.get("completed_tasks", [])
                                await websocket.send_json({
                                    "type": "task_status",
                                    "pending": len(task_queue),
                                    "completed": len(completed)
                                })

                            await websocket.send_json({
                                "type": "agent",
                                "agent": node_name,
                                "agent_display": agent_display
                            })

                            # 累积状态
                            for key, value in node_output.items():
                                if key in accumulated_state:
                                    if isinstance(value, list) and isinstance(accumulated_state[key], list):
                                        accumulated_state[key].extend(value)
                                    elif isinstance(value, dict) and isinstance(accumulated_state[key], dict):
                                        accumulated_state[key].update(value)
                                    else:
                                        accumulated_state[key] = value
                                else:
                                    accumulated_state[key] = value

                            # 发送 Skill 调用信息
                            if "skill_calls" in node_output:
                                for skill_call in node_output["skill_calls"]:
                                    await websocket.send_json({
                                        "type": "skill",
                                        "skill": skill_call.get("skill", "unknown"),
                                        "skill_display": skill_call.get("display_name", skill_call.get("skill", "unknown"))
                                    })

                            # 发送消息内容
                            if "messages" in node_output:
                                messages = node_output["messages"]
                                if messages:
                                    last_msg = messages[-1]
                                    if hasattr(last_msg, 'content') and last_msg.content:
                                        await websocket.send_json({
                                            "type": "chunk",
                                            "content": last_msg.content,
                                            "agent": node_name
                                        })

                    # 发送代码
                    current_code = accumulated_state.get("current_code", "") or accumulated_state.get("code", "")
                    if current_code:
                        await websocket.send_json({
                            "type": "code",
                            "content": current_code
                        })

                    # 发送报告
                    report = accumulated_state.get("report", "")
                    if report:
                        await websocket.send_json({
                            "type": "report",
                            "content": report
                        })

                    # 发送图表路径（转换为 HTTP URL）
                    figures = accumulated_state.get("figures", [])
                    if figures:
                        figure_urls = []
                        for fig_path in figures:
                            if isinstance(fig_path, str):
                                if "outputs" in fig_path:
                                    relative_path = fig_path.split("outputs")[-1].replace("\\", "/").lstrip("/")
                                    figure_urls.append(f"/static/figures/{relative_path}")
                                else:
                                    fig_name = Path(fig_path).name
                                    figure_urls.append(f"/static/figures/{fig_name}")
                        if figure_urls:
                            await websocket.send_json({
                                "type": "figures",
                                "content": figure_urls
                            })

                    # 发送完成标记
                    await websocket.send_json({"type": "done"})

                except Exception as e:
                    logger.error(f"Graph 执行错误: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"处理失败: {str(e)}"
                    })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知的消息类型: {message_type}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket 连接断开: session_id={session_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"服务器错误: {str(e)}"
            })
        except:
            pass
    finally:
        logger.info(f"WebSocket 连接关闭: session_id={session_id}")
