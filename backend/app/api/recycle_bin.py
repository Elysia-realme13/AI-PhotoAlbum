"""
回收站 API 路由
独立的路由文件，避免与 /{photo_id} 泛匹配冲突
"""
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_required_user
from app.crud.photo import (
    batch_permanent_delete,
    batch_restore,
    get_deleted_photo_file_paths,
    get_deleted_photos,
    get_photo_by_id_any,
    permanent_delete_photo,
)
from app.database.session import get_db
from app.database.storage import storage
from app.models.user import User
from app.schemas.photo import BatchPhotoRequest, PhotoListResponse, PhotoResponse
from app.schemas.response import BaseResponse

logger = logging.getLogger("app.api.recycle_bin")

router = APIRouter(prefix="/api/photos/recycle-bin", tags=["回收站"])


@router.get("/list", response_model=PhotoListResponse)
def list_recycle_bin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取回收站中的照片列表"""
    photos = get_deleted_photos(db, str(current_user.id))
    items = [PhotoResponse.model_validate(p) for p in photos]
    return PhotoListResponse(
        total=len(items),
        page=1,
        page_size=len(items),
        items=items,
    )


@router.post("/empty")
def empty_recycle_bin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """清空回收站"""
    photos = get_deleted_photos(db, str(current_user.id))
    count = 0
    for photo in photos:
        # 删除原图文件
        if photo.file_path and os.path.exists(photo.file_path):
            storage.delete_file(photo.file_path)
        # 删除缩略图文件
        thumb_path = storage.thumbnail_dir / f"{photo.id}_thumb.jpg"
        if thumb_path.exists():
            thumb_path.unlink()
        permanent_delete_photo(db, photo)
        count += 1
    return {"message": f"已清空回收站，共删除 {count} 张照片", "count": count}


@router.delete("/{photo_id}/permanent")
def permanent_delete(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """永久删除单张照片"""
    photo = get_photo_by_id_any(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")
    if str(photo.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权操作此照片")
    if not photo.is_deleted:
        raise HTTPException(400, "请先移入回收站再彻底删除")
    permanent_delete_photo(db, photo)
    return {"message": "已永久删除", "photo_id": photo_id}


@router.post("/{photo_id}/restore")
def restore_single(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """恢复单张照片"""
    photo = get_photo_by_id_any(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")
    if str(photo.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权操作此照片")
    if not photo.is_deleted:
        raise HTTPException(400, "照片不在回收站中")
    photo.is_deleted = False
    photo.deleted_at = None
    db.commit()
    return {"message": "已恢复", "photo_id": photo_id}


@router.post("/batch/restore", response_model=BaseResponse[dict])
def batch_restore_photos(
    req: BatchPhotoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """批量恢复照片（从回收站恢复）"""
    photo_ids = [uuid.UUID(pid) for pid in req.photo_ids]
    success, fail = batch_restore(db, photo_ids, current_user.id)
    return BaseResponse(data={"success_count": success, "fail_count": fail})


@router.post("/batch/permanent", response_model=BaseResponse[dict])
def batch_permanent_delete_photos(
    req: BatchPhotoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """批量永久删除照片（彻底删除）"""
    photo_ids = [uuid.UUID(pid) for pid in req.photo_ids]

    # 获取文件路径（一次查询，避免重复）
    file_paths = get_deleted_photo_file_paths(db, photo_ids, current_user.id)

    # 删除原图文件 + 缩略图文件
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                storage.delete_file(file_path)
        except OSError as e:
            logger.warning(f"删除文件失败 {file_path}: {e}")

    # 删除缩略图（根据 photo_id 推导）
    for pid in photo_ids:
        thumb_path = storage.thumbnail_dir / f"{pid}_thumb.jpg"
        try:
            if thumb_path.exists():
                thumb_path.unlink()
        except OSError as e:
            logger.warning(f"删除缩略图失败 {thumb_path}: {e}")

    # 批量删除数据库记录
    success, fail = batch_permanent_delete(db, photo_ids, current_user.id)
    return BaseResponse(data={"success_count": success, "fail_count": fail})
