"""
任务调度器 — 基于 APScheduler 定时驱动任务分发器

在 FastAPI lifespan 启动时拉起 BackgroundScheduler，按 settings.TASK_POLL_INTERVAL
周期轮询 pending 任务并交给 dispatcher.run_pending_tasks 消费。

单进程/单调度器设计：max_instances=1 + coalesce=True，避免上一轮未跑完时任务堆叠。
每次 tick 使用独立 SessionLocal，用完即关。
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config.settings import settings
from app.database.session import SessionLocal
from app.tasks.dispatcher import run_pending_tasks

logger = logging.getLogger("app.tasks.scheduler")


def _tick() -> None:
    """单次轮询：消费一批 pending 任务"""
    db = SessionLocal()
    try:
        stats = run_pending_tasks(db, limit=settings.TASK_BATCH_SIZE)
        if stats["total"]:
            logger.info(
                f"任务分发: completed={stats['completed']} "
                f"failed={stats['failed']} total={stats['total']}"
            )
    except Exception as e:  # noqa: BLE001
        logger.error(f"任务轮询异常: {e}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """构造并启动后台调度器"""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _tick,
        trigger="interval",
        seconds=settings.TASK_POLL_INTERVAL,
        max_instances=1,
        coalesce=True,
        id="task_dispatcher",
    )
    scheduler.start()
    logger.info(f"任务调度器已启动，轮询间隔 {settings.TASK_POLL_INTERVAL}s")
    return scheduler


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    """关闭调度器"""
    try:
        scheduler.shutdown(wait=False)
        logger.info("任务调度器已关闭")
    except Exception:  # noqa: BLE001
        pass


__all__ = ["start_scheduler", "shutdown_scheduler"]
