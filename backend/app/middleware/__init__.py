"""
请求日志中间件
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的耗时和状态码"""

    async def dispatch(self, request: Request, call_next):
        # 跳过静态文件请求
        if request.url.path.startswith("/api/medias"):
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} "
            f"({process_time:.1f}ms)"
        )
        return response
