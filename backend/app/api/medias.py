"""
媒体文件服务
提供原始图片和缩略图的文件访问
"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.crud.photo import get_photo_by_id
from app.api.deps import get_current_user
from app.config.settings import settings

router = APIRouter(prefix="/api/medias", tags=["媒体"])


@router.get("/{photo_id}/thumbnail")
def serve_thumbnail(
    photo_id: str,
    db: Session = Depends(get_db),
):
    """获取照片缩略图（无需登录，用于页面展示）"""
    photo = get_photo_by_id(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    thumb_dir = Path(settings.THUMBNAIL_DIR)
    thumb_path = thumb_dir / f"{photo.filename}_thumb.jpg"

    if not thumb_path.exists():
        # 回退到原始文件
        orig_path = Path(photo.file_path)
        if orig_path.exists():
            return FileResponse(str(orig_path), media_type="image/jpeg")
        raise HTTPException(404, "缩略图不存在")

    return FileResponse(str(thumb_path), media_type="image/jpeg")


@router.get("/{photo_id}/file")
def serve_file(
    photo_id: str,
    db: Session = Depends(get_db),
):
    """获取原始照片文件（需登录）"""
    photo = get_photo_by_id(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    file_path = Path(photo.file_path)
    if not file_path.exists():
        raise HTTPException(404, "文件不存在")

    # 判断 MIME 类型
    ext = file_path.suffix.lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.heic': 'image/heic',
        '.heif': 'image/heif',
    }
    media_type = mime_map.get(ext, 'application/octet-stream')

    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=photo.original_name or photo.filename,
    )
