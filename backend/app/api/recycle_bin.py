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
    get_photo_by_id,
    get_photo_list,
    permanent_delete_photo,
)
from app.database.session import get_db
from app.database.storage import storage
from app.models.user import User
from app.schemas.photo import BatchPhotoRequest, PhotoListItem
from app.schemas.response import BaseResponse, PaginatedData

logger = logging.getLogger("app.api.recycle_bin")

router = APIRouter(prefix="/api/photos/recycle-bin", tags=["回收站"])


@router.get("/list", response_model=BaseResponse[PaginatedData])
def list_recycle_bin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取回收站中的照片列表"""
    photos, _total = get_photo_list(
        db=db, owner_id=current_user.id, page=1, page_size=500, is_deleted=True,
    )
    items = [_to_list_item(p) for p in photos]
    return BaseResponse(data=PaginatedData(
        total=len(items), page=1, page_size=len(items), items=items,
    ))


@router.post("/empty")
def empty_recycle_bin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """清空回收站"""
    photos, _total = get_photo_list(
        db=db, owner_id=current_user.id, page=1, page_size=10000, is_deleted=True,
    )
    count = 0
    for photo in photos:
        if photo.file_path and os.path.exists(photo.file_path):
            storage.delete_file(photo.file_path)
        thumb_path = storage.thumbnail_dir / f"{photo.filename}_thumb.jpg"
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
    photo = get_photo_by_id(db, uuid.UUID(photo_id), owner_id=current_user.id, include_deleted=True)
    if not photo:
        raise HTTPException(404, "照片不存在")
    if not photo.is_deleted:
        raise HTTPException(400, "请先移入回收站再彻底删除")
    permanent_delete_photo(db, photo)
    return {"message": "已永久删除", "photo_id": photo_id}


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

    file_paths = get_deleted_photo_file_paths(db, photo_ids, current_user.id)

    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                storage.delete_file(file_path)
        except OSError as e:
            logger.warning(f"删除文件失败 {file_path}: {e}")

    # 缩略图按存储文件名 {filename}_thumb.jpg 命名，需取回照片对象
    for pid in photo_ids:
        photo = get_photo_by_id(db, pid, owner_id=current_user.id, include_deleted=True)
        if not photo or not photo.filename:
            continue
        thumb_path = storage.thumbnail_dir / f"{photo.filename}_thumb.jpg"
        try:
            if thumb_path.exists():
                thumb_path.unlink()
        except OSError as e:
            logger.warning(f"删除缩略图失败 {thumb_path}: {e}")

    success, fail = batch_permanent_delete(db, photo_ids, current_user.id)
    return BaseResponse(data={"success_count": success, "fail_count": fail})


def _to_list_item(photo) -> PhotoListItem:
    """从 ORM 对象构建列表项"""
    return PhotoListItem(
        id=str(photo.id),
        filename=photo.filename,
        original_name=photo.original_name,
        width=photo.width,
        height=photo.height,
        photo_time=photo.photo_time,
        upload_time=photo.upload_time,
        file_type=photo.file_type.value if hasattr(photo.file_type, 'value') else str(photo.file_type),
        file_size=photo.file_size,
        is_deleted=photo.is_deleted,
        deleted_at=photo.deleted_at,
    )
