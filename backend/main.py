"""
AI-PhotoAlbum 后端应用入口
FastAPI 应用工厂 + 路由注册 + 生命周期管理
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 确保所有模型被导入（使 Base.metadata 注册所有表）
import app.models  # noqa: F401
from app.api.agent import router as agent_router
from app.api.album import router as album_router

# 路由模块
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.face import router as face_router
from app.api.models import router as models_router
from app.api.photo import router as photo_router
from app.api.recycle_bin import router as recycle_bin_router
from app.api.search import router as search_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router

# 训练与管理路由
from app.api.training import router as training_router
from app.config.settings import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logger import setup_logger
from app.middleware import RequestLoggerMiddleware

# 初始化日志
logger = setup_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info("=" * 60)

    # 初始化数据库表
    from sqlalchemy import text

    from app.database.session import Base, engine
    logger.info(f"数据库: {settings.DATABASE_URL[:50]}...")

    # 启用 pgvector 扩展（仅 PostgreSQL）
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception:
        pass  # SQLite 不支持，忽略

    logger.info("正在创建数据库表...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建/检查完成")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        logger.error("请检查:")
        logger.error("  1. PostgreSQL 是否已启动? docker compose up -d postgres")
        logger.error(
            "  2. 或使用 SQLite 测试: "
            "DATABASE_URL=sqlite:///./data/app.db uv run uvicorn main:app ..."
        )
        raise

    # 自动迁移：create_all 不会给已有表添加新列，需手动补齐
    migrations = [
        "ALTER TABLE faces ADD COLUMN IF NOT EXISTS face_name VARCHAR(100)",
        "ALTER TABLE faces ADD COLUMN IF NOT EXISTS face_aliases JSON",
        "ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'object_detection'",
        "ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'geocode'",
    ]
    for sql in migrations:
        try:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
        except Exception:
            pass

    # 启动任务调度器（消费上传后创建的 AI 分析任务）
    _app.state.scheduler = None
    if settings.TASK_SCHEDULER_ENABLED:
        from app.tasks.scheduler import start_scheduler
        _app.state.scheduler = start_scheduler()

    yield

    if getattr(_app.state, "scheduler", None):
        from app.tasks.scheduler import shutdown_scheduler
        shutdown_scheduler(_app.state.scheduler)

    logger.info("服务已关闭")


# ── 创建 FastAPI 实例 ────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 智能相册 — 让每一张照片都成为值得珍藏的记忆",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── 注册异常处理器 ──────────────────────────────────
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# ── 注册中间件 ─────────────────────────────────────
app.add_middleware(RequestLoggerMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ───────────────────────────────────────
app.include_router(auth_router)
app.include_router(system_router)
app.include_router(photo_router)
app.include_router(album_router)
app.include_router(face_router)
app.include_router(search_router)
app.include_router(agent_router)
app.include_router(tasks_router)
app.include_router(recycle_bin_router)

# 注册训练与管理路由
app.include_router(training_router)
app.include_router(models_router)
app.include_router(datasets_router)

# ── 挂载静态文件 ───────────────────────────────────
_avatar_dir = Path(settings.AVATAR_DIR)
_avatar_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/avatars", StaticFiles(directory=str(_avatar_dir)), name="avatars")


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
