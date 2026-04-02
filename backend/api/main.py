"""FastAPI 应用入口"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import chat, sessions, upload
from backend.api.websocket.handler import websocket_chat

# 创建 FastAPI 应用
app = FastAPI(
    title="多 Agent 数据分析平台",
    description="基于 LangGraph 的自驱型多 Agent 数据分析系统",
    version="1.0.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/chat")
app.include_router(sessions.router, prefix="/api/sessions")
app.include_router(upload.router, prefix="/api/upload")


# WebSocket 路由
@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 聊天端点"""
    await websocket_chat(websocket, session_id)


@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "service": "多 Agent 数据分析平台",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}
