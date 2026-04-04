"""
聊天相关 API 路由

提供同步和异步聊天接口。
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求模型"""
    session_id: str
    message: str
    stream: bool = False  # 是否使用流式响应


class ChatResponse(BaseModel):
    """聊天响应模型"""
    session_id: str
    response: str
    code: Optional[str] = None
    figures: Optional[List[str]] = None
    report: Optional[str] = None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    发送消息（同步）

    Args:
        request: 聊天请求

    Returns:
        ChatResponse: AI 回复和生成的内容
    """
    try:
        # 导入在函数内部以避免循环依赖
        from src.graph.builder import get_graph
        from src.persistence.session_store import SessionStore

        # 获取 Graph
        graph = get_graph(with_checkpointer=False)

        # 加载会话数据
        store = SessionStore()
        session = store.get_session(request.session_id)

        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 构建状态
        state = {
            "session_id": request.session_id,  # 传递 session_id 用于数据获取
            "messages": [HumanMessage(content=request.message)],
            "datasets": store.get_datasets(request.session_id),
            "active_dataset_index": 0,
            "retry_count": 0,
        }

        # 调用 Graph
        result = graph.invoke(
            state,
            config={"configurable": {"thread_id": request.session_id}}
        )

        # 提取结果
        response_data = {
            "session_id": request.session_id,
            "response": "",
        }

        # 提取最后的 AI 回复
        if "messages" in result:
            messages = result["messages"]
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    response_data["response"] = last_msg.content
                else:
                    response_data["response"] = str(last_msg)

                # 保存消息到数据库
                store.add_message(
                    request.session_id,
                    "user",
                    request.message
                )
                store.add_message(
                    request.session_id,
                    "assistant",
                    response_data["response"]
                )

        # 提取代码
        if "current_code" in result:
            code = result.get("current_code")
            if code:
                response_data["code"] = code
                # 保存代码产物
                store.save_artifact(
                    request.session_id,
                    "code",
                    content=code
                )

        # 提取图表
        if "figures" in result and result["figures"]:
            response_data["figures"] = result["figures"]
            # 保存图表路径
            for fig_path in result["figures"]:
                store.save_artifact(
                    request.session_id,
                    "figure",
                    file_path=fig_path
                )

        # 提取报告
        if "report" in result:
            report = result.get("report")
            if report:
                response_data["report"] = report
                # 保存报告产物
                store.save_artifact(
                    request.session_id,
                    "report",
                    content=report
                )

        # 更新数据集（如果有的话）
        if "datasets" in result and result["datasets"]:
            store.save_datasets(request.session_id, result["datasets"])

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    发送消息（流式响应）

    Args:
        request: 聊天请求

    Returns:
        StreamingResponse: 流式响应
    """
    from fastapi.responses import StreamingResponse
    from src.graph.builder import get_graph
    from src.persistence.session_store import SessionStore

    # 异步生成器
    async def generate():
        try:
            # 获取 Graph
            graph = get_graph(with_checkpointer=False)

            # 加载会话数据
            store = SessionStore()

            # 构建状态
            state = {
                "messages": [HumanMessage(content=request.message)],
                "datasets": store.get_datasets(request.session_id) if store.get_session(request.session_id) else [],
                "active_dataset_index": 0,
            }

            # 流式输出
            async for chunk in graph.astream(
                state,
                config={"configurable": {"thread_id": request.session_id}}
            ):
                if "messages" in chunk:
                    messages = chunk["messages"]
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, 'content') and last_msg.content:
                            # 流式发送内容片段
                            yield f"data: {last_msg.content}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
