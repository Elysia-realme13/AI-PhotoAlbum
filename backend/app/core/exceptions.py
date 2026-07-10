"""
全局异常处理
自定义异常类 + FastAPI 异常处理器
"""
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request


class AppException(Exception):
    """应用自定义异常基类"""

    def __init__(self, message: str, status_code: int = 400, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


async def app_exception_handler(request: Request, exc: AppException):
    """处理自定义异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.detail},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTP 异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "detail": {}},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求参数验证异常"""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
            }
        )
    return JSONResponse(
        status_code=422,
        content={"error": "请求参数验证失败", "detail": errors},
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的通用异常"""
    import logging

    logger = logging.getLogger("app.exceptions")
    logger.error(f"未捕获的异常: {type(exc).__name__}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "detail": str(exc)},
    )
