"""
系统 API 路由
健康检查 / 服务状态
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["系统"])


@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "message": "AI-PhotoAlbum service is running"}
