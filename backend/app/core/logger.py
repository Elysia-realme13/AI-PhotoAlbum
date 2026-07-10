"""
日志模块
提供统一的日志配置和获取接口
"""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "app") -> logging.Logger:
    """初始化并返回日志记录器"""
    from app.config.settings import settings

    log_dir = Path("./data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 格式
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler（按日滚动可后续用 TimedRotatingFileHandler）
    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "app") -> logging.Logger:
    """获取指定名称的日志记录器"""
    return logging.getLogger(name)
