"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration for the GEO AI Platform."""

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "AI引流 Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://geoai:geoai@localhost:5432/geoai_platform"
    DATABASE_URL_SYNC: str = "postgresql://geoai:geoai@localhost:5432/geoai_platform"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # ── Chroma Vector Store ──────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # ── JWT Authentication ───────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production-use-a-strong-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── File Storage ─────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── LLM: DeepSeek (综合分析与内容生成) ──────────────────────
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "deepseek-chat"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # ── 豆包 (火山引擎 Ark) ─────────────────────────────────────
    DOUBAO_API_KEY: Optional[str] = None
    DOUBAO_API_BASE: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "ep-20260707115715-h2ptf"

    # ── 文心一言 (百度千帆) ─────────────────────────────────────
    WENXIN_API_KEY: Optional[str] = None
    WENXIN_API_BASE: str = "https://qianfan.baidubce.com/v2"
    WENXIN_MODEL: str = "ernie-4.0-turbo-128k"

    # ── 通义千问 (阿里云 DashScope) ─────────────────────────────
    QIANWEN_API_KEY: Optional[str] = None
    QIANWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QIANWEN_MODEL: str = "qwen-plus"

    # ── 智谱 GLM ────────────────────────────────────────────────
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODEL: str = "glm-4-flash"

    # ── Kimi (Moonshot) ─────────────────────────────────────────
    KIMI_API_KEY: Optional[str] = None
    KIMI_API_BASE: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k"

    # ── 腾讯混元 ────────────────────────────────────────────────
    HUNYUAN_API_KEY: Optional[str] = None
    HUNYUAN_API_BASE: str = "https://api.hunyuan.cloud.tencent.com/v1"
    HUNYUAN_MODEL: str = "hunyuan-pro"

    # ── 讯飞星火 (iFlytek Spark) ───────────────────────────────
    XINGHUO_API_KEY: Optional[str] = None
    XINGHUO_API_SECRET: Optional[str] = None
    XINGHUO_APP_ID: Optional[str] = None
    XINGHUO_API_BASE: str = "https://spark-api-open.xf-yun.com/v1"
    XINGHUO_MODEL: str = "4.0Ultra"

    # ── Celery ──────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ── Embedding ────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "openai"  # "openai" | "local"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_CHUNK_SIZE: int = 1000
    EMBEDDING_CHUNK_OVERLAP: int = 200

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:80"]

    # ── APScheduler ──────────────────────────────────────────────
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


settings = Settings()
