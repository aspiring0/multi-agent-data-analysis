"""FastAPI 应用入口"""

from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# 挂载静态文件目录（图表）- 图表保存在 data/outputs/figures_xxx/ 下
FIGURES_DIR = Path(__file__).parent.parent.parent / "data" / "outputs"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/figures", StaticFiles(directory=str(FIGURES_DIR)), name="figures")

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


@app.get("/health/detailed")
async def health_detailed():
    """详细健康检查端点"""
    import shutil
    from datetime import datetime

    checks = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {},
    }

    # 检查数据库连接
    try:
        from src.persistence.session_store import SessionStore
        store = SessionStore()
        store.list_sessions()
        checks["components"]["database"] = {"status": "ok", "type": "sqlite"}
    except Exception as e:
        checks["components"]["database"] = {"status": "error", "message": str(e)}
        checks["status"] = "degraded"

    # 检查 PostgreSQL (可选)
    try:
        import psycopg2
        from configs.settings import settings
        conn = psycopg2.connect(settings.POSTGRES_URI)
        conn.close()
        checks["components"]["postgres"] = {"status": "ok"}
    except Exception as e:
        checks["components"]["postgres"] = {"status": "unavailable", "message": str(e)}

    # 检查 LLM 配置
    from configs.settings import settings
    if settings.DEEPSEEK_API_KEY:
        checks["components"]["llm"] = {"status": "configured", "model": settings.DEEPSEEK_MODEL}
    else:
        checks["components"]["llm"] = {"status": "not_configured"}
        checks["status"] = "degraded"

    # 检查磁盘空间
    try:
        total, used, free = shutil.disk_usage("/")
        checks["components"]["disk"] = {
            "status": "ok",
            "free_gb": round(free / (1024**3), 2),
            "used_percent": round(used / total * 100, 1),
        }
    except Exception:
        checks["components"]["disk"] = {"status": "unknown"}

    return checks
