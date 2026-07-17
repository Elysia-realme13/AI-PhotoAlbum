"""
全局配置模块
使用 pydantic-settings 从环境变量和 .env 文件加载配置
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用全局配置"""

    # ── 应用信息 ──────────────────────────────────────
    APP_NAME: str = "AI-PhotoAlbum"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── 数据库 ────────────────────────────────────────
    DATABASE_URL: str = "postgresql://album:album@localhost:5433/photo_album"

    # ── JWT 认证 ──────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 小时

    # ── 大模型 API ────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    # ── MinIO 对象存储 ────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "photo-album"
    MINIO_SECURE: bool = False

    # ── 文件存储 ───────────────────────────────────────
    UPLOAD_DIR: str = "./data/uploads"
    THUMBNAIL_DIR: str = "./data/thumbnails"
    AVATAR_DIR: str = "./data/avatars"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── AI 模型路径 ────────────────────────────────────
    MODELS_DIR: str = "./data/models"

    # ── CORS ──────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# 全局配置单例
settings = Settings()
