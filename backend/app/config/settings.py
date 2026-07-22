"""
全局配置模块
使用 pydantic-settings 从环境变量和 .env 文件加载配置
"""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用全局配置"""

    # -- 应用信息 ----------------------------------------
    APP_NAME: str = "AI-PhotoAlbum"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # -- 数据库 ------------------------------------------
    DATABASE_URL: str = "postgresql://album:album@localhost:5433/photo_album"

    # -- JWT 认证 ----------------------------------------
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 小时

    # -- 大模型 API --------------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    # -- 视觉模型 API（用于图像描述，需多模态模型）--------
    VISION_API_KEY: str = ""
    VISION_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    VISION_MODEL: str = "glm-4.6v-flashx"

    # -- MinIO 对象存储 ----------------------------------
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "photo-album"
    MINIO_SECURE: bool = False

    # -- 文件存储 ----------------------------------------
    UPLOAD_DIR: str = "./data/uploads"
    THUMBNAIL_DIR: str = "./data/thumbnails"
    AVATAR_DIR: str = "./data/avatars"
    MAX_UPLOAD_SIZE_MB: int = 50

    # -- 图片压缩 ----------------------------------------
    MAX_IMAGE_LONG_EDGE: int = 2560
    IMAGE_QUALITY: int = 85

    # -- AI 模型路径 -------------------------------------
    MODELS_DIR: str = "./data/models"
    # -- 日志目录 ----------------------------------------
    LOGS_DIR: str = "./data/logs"

    # -- 任务调度器 --------------------------------------
    TASK_SCHEDULER_ENABLED: bool = True
    TASK_POLL_INTERVAL: int = 15  # 轮询间隔（秒）
    TASK_BATCH_SIZE: int = 10  # 单次处理任务数上限

    # -- 反向地理编码 ------------------------------------
    GEOCODING_ENABLED: bool = True
    # 离线行政区边界（市级，随仓库分发）；命中则返回中文省/市名，无需联网
    GEO_BOUNDARY_FILE: str = "./data/geo/china_city.geojson"
    # 离线未命中（境外坐标/数据缺失）时回退的在线 Nominatim 端点
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/reverse"
    NOMINATIM_USER_AGENT: str = "AI-PhotoAlbum/0.1 (self-hosted)"
    GEOCODING_LANG: str = "zh-CN"
    GEOCODING_MIN_INTERVAL: float = 1.0  # Nominatim 使用策略：≥1s/次

    # -- CORS --------------------------------------------
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

# 将相对路径转换为相对于项目根目录的绝对路径
# 先尝试 4 层 parent（本地开发），再试 3 层 parent（Docker 挂载）
_FILE = Path(__file__).resolve()
for _n in (4, 3):
    _PROJECT_ROOT = _FILE.parents[_n - 1]
    if (_PROJECT_ROOT / "data" / "models").is_dir():
        break
else:
    _PROJECT_ROOT = _FILE.parents[2]  # fallback

_RELATIVE_PATH_FIELDS = [
    "UPLOAD_DIR",
    "THUMBNAIL_DIR",
    "AVATAR_DIR",
    "MODELS_DIR",
    "LOGS_DIR",
    "GEO_BOUNDARY_FILE",
]
for _field in _RELATIVE_PATH_FIELDS:
    _val: str = getattr(settings, _field)
    if _val.startswith("./"):
        _abs = (_PROJECT_ROOT / _val[2:]).resolve()
        object.__setattr__(settings, _field, str(_abs))

# 启动时打印解析后的路径，用于验证
