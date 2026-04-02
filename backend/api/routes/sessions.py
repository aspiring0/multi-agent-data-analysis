"""
会话管理 API 路由

提供会话的创建、查询、删除等功能。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.persistence.session_store import SessionStore

router = APIRouter(tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    name: str


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    name: str
    created_at: str
    updated_at: str
    message_count: int
    dataset_count: int


@router.post("/", response_model=SessionResponse)
def create_session(request: CreateSessionRequest):
    """
    创建新会话

    Args:
        request: 创建会话请求

    Returns:
        SessionResponse: 创建的会话信息
    """
    import uuid

    store = SessionStore()

    # 生成会话 ID
    session_id = uuid.uuid4().hex[:8]

    # 创建会话
    store.create_session(session_id, request.name)

    return SessionResponse(
        id=session_id,
        name=request.name,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        message_count=0,
        dataset_count=0,
    )


@router.get("/")
def list_sessions():
    """
    获取所有会话列表

    Returns:
        list: 会话列表
    """
    store = SessionStore()
    sessions = store.list_sessions()
    return sessions


@router.get("/{session_id}", response_model=dict)
def get_session(session_id: str):
    """
    获取会话详情

    Args:
        session_id: 会话 ID

    Returns:
        dict: 会话详情（包含消息、数据集、产物等）
    """
    store = SessionStore()

    # 获取会话基本信息
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取消息
    messages = store.get_messages(session_id)

    # 获取数据集
    datasets = store.get_datasets(session_id)

    # 获取产物
    code_artifacts = store.get_artifacts(session_id, "code")
    report_artifacts = store.get_artifacts(session_id, "report")
    figure_artifacts = store.get_artifacts(session_id, "figure")

    return {
        "id": session_id,
        "name": session.get("name"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "messages": messages,
        "datasets": datasets,
        "current_code": code_artifacts[0]["content"] if code_artifacts else "",
        "report": report_artifacts[0]["content"] if report_artifacts else "",
        "figures": [a["file_path"] for a in figure_artifacts],
    }


@router.delete("/{session_id}")
def delete_session(session_id: str):
    """
    删除会话

    Args:
        session_id: 会话 ID

    Returns:
        dict: 删除结果
    """
    store = SessionStore()
    store.delete_session(session_id)
    return {"session_id": session_id, "deleted": True}


@router.patch("/{session_id}/name")
def update_session_name(session_id: str, name: str):
    """
    更新会话名称

    Args:
        session_id: 会话 ID
        name: 新名称

    Returns:
        dict: 更新后的会话信息
    """
    store = SessionStore()
    store.update_session_name(session_id, name)
    return {"session_id": session_id, "name": name}
