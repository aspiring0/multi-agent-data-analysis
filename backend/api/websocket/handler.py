"""
WebSocket 处理器

处理实时聊天通信和流式响应。
"""
import logging
from pathlib import Path
from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

from src.graph.builder import get_graph
from src.persistence.session_store import SessionStore

logger = logging.getLogger(__name__)


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

                # 获取 Graph
                graph = get_graph(with_checkpointer=False)

                # 构建状态
                state = {
                    "messages": [HumanMessage(content=user_message)],
                    "datasets": store.get_datasets(session_id),
                    "active_dataset_index": 0,
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

                            # 发送消息内容
                            if "messages" in node_output:
                                messages = node_output["messages"]
                                if messages:
                                    last_msg = messages[-1]
                                    if hasattr(last_msg, 'content') and last_msg.content:
                                        await websocket.send_json({
                                            "type": "chunk",
                                            "content": last_msg.content
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
