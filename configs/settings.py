"""
全局配置管理
通过 .env 文件或环境变量加载配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Settings:
    """应用配置"""

    # ---- LLM 配置 ----
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # ---- 沙箱配置 ----
    SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "30"))
    SANDBOX_MAX_MEMORY_MB: int = int(os.getenv("SANDBOX_MAX_MEMORY_MB", "512"))

    # ---- 数据库配置 ----
    POSTGRES_URI: str = os.getenv(
        "POSTGRES_URI",
        "postgresql://postgres:postgres@localhost:5432/langgraph"
    )
    CHECKPOINTER_TYPE: str = os.getenv("CHECKPOINTER_TYPE", "postgres")  # postgres | memory

    # ---- 路径配置 ----
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    OUTPUT_DIR: Path = DATA_DIR / "outputs"

    # ---- 日志配置 ----
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ---- Graph 配置 ----
    USE_GRAPH_V2: bool = os.getenv("USE_GRAPH_V2", "true").lower() in ("true", "1", "yes")
    # V2: 多轮调度模式 (Coordinator V2)
    # V1: 单次路由模式 (原始 Coordinator)

    def __init__(self):
        """初始化时确保必要目录存在"""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """验证配置完整性，返回错误列表"""
        errors = []
        if not self.DEEPSEEK_API_KEY:
            errors.append("DEEPSEEK_API_KEY 未设置")
        return errors


# 全局单例
settings = Settings()
