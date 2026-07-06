"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration for the GEO AI Platform."""

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "GEO AI Platform"
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

    # ── LLM Providers ────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"  # "openai" | "anthropic"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

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
