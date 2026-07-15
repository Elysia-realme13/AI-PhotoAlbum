"""
相册 API 路由
"""
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.schemas.response import BaseResponse, PaginatedData
from app.schemas.album import AlbumCreate, AlbumUpdate, AlbumResponse
from app.crud import album as album_crud
from app.crud import photo as photo_crud

logger = logging.getLogger("app.api.album")

router = APIRouter(prefix="/api/albums", tags=["相册"])


@router.get("", response_model=BaseResponse[List[AlbumResponse]])
def get_albums(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    获取用户的所有相册
    """
    albums = album_crud.get_user_albums(db, current_user.id)
    
    result = []
    for album in albums:
        photo_count = album_crud.get_album_photo_count(db, album.id)
        result.append(AlbumResponse(
            id=str(album.id),
            owner_id=str(album.owner_id),
            name=album.name,
            description=album.description,
            cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
            is_system=album.is_system,
            album_type=album.album_type.value if hasattr(album.album_type, 'value') else str(album.album_type),
            conditions=album.conditions,
            photo_count=photo_count,
            created_at=album.created_at,
            updated_at=album.updated_at,
        ))
    
    return BaseResponse(data=result)


@router.post("", response_model=BaseResponse[AlbumResponse], status_code=201)
def create_album(
    data: AlbumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    创建相册
    """
    album = album_crud.create_album(
        db,
        owner_id=current_user.id,
        name=data.name,
        description=data.description,
        album_type=data.album_type,
        conditions=data.conditions,
    )
    
    return BaseResponse(data=AlbumResponse(
        id=str(album.id),
        owner_id=str(album.owner_id),
        name=album.name,
        description=album.description,
        cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
        is_system=album.is_system,
        album_type=album.album_type.value if hasattr(album.album_type, 'value') else str(album.album_type),
        conditions=album.conditions,
        photo_count=0,
        created_at=album.created_at,
        updated_at=album.updated_at,
    ))


@router.get("/{album_id}", response_model=BaseResponse[AlbumResponse])
def get_album(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    获取相册详情
    """
    try:
        album_uuid = uuid.UUID(album_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的相册ID")
    
    album = album_crud.get_album_by_id(db, album_uuid)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    
    if album.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此相册")
    
    photo_count = album_crud.get_album_photo_count(db, album.id)
    
    return BaseResponse(data=AlbumResponse(
        id=str(album.id),
        owner_id=str(album.owner_id),
        name=album.name,
        description=album.description,
        cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
        is_system=album.is_system,
        album_type=album.album_type.value if hasattr(album.album_type, 'value') else str(album.album_type),
        conditions=album.conditions,
        photo_count=photo_count,
        created_at=album.created_at,
        updated_at=album.updated_at,
    ))


@router.put("/{album_id}", response_model=BaseResponse[AlbumResponse])
def update_album(
    album_id: str,
    data: AlbumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    更新相册
    """
    try:
        album_uuid = uuid.UUID(album_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的相册ID")
    
    album = album_crud.get_album_by_id(db, album_uuid)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    
    if album.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此相册")
    
    update_data = data.dict(exclude_unset=True)
    if 'cover_photo_id' in update_data and update_data['cover_photo_id']:
        try:
            uuid.UUID(update_data['cover_photo_id'])
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的照片ID")
    
    album = album_crud.update_album(db, album, **update_data)
    photo_count = album_crud.get_album_photo_count(db, album.id)
    
    return BaseResponse(data=AlbumResponse(
        id=str(album.id),
        owner_id=str(album.owner_id),
        name=album.name,
        description=album.description,
        cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
        is_system=album.is_system,
        album_type=album.album_type.value if hasattr(album.album_type, 'value') else str(album.album_type),
        conditions=album.conditions,
        photo_count=photo_count,
        created_at=album.created_at,
        updated_at=album.updated_at,
    ))


@router.delete("/{album_id}", response_model=BaseResponse)
def delete_album(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    删除相册
    """
    try:
        album_uuid = uuid.UUID(album_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的相册ID")
    
    album = album_crud.get_album_by_id(db, album_uuid)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    
    if album.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此相册")
    
    if album.is_system:
        raise HTTPException(status_code=400, detail="系统相册不能删除")
    
    success = album_crud.delete_album(db, album)
    if not success:
        raise HTTPException(status_code=500, detail="删除相册失败")
    
    return BaseResponse(msg="相册删除成功")


@router.get("/{album_id}/photos", response_model=BaseResponse[PaginatedData])
def get_album_photos(
    album_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    获取相册中的照片
    """
    try:
        album_uuid = uuid.UUID(album_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的相册ID")
    
    album = album_crud.get_album_by_id(db, album_uuid)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    
    if album.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此相册")
    
    total, photos = album_crud.get_album_photos(db, album_uuid, page, page_size)
    
    items = []
    for photo in photos:
        tags = None
        if photo.tags:
            tags = [tag.tag_name for tag in photo.tags]
        
        quality_score = None
        if photo.description_info:
            quality_score = photo.description_info.quality_score
        
        items.append({
            "id": str(photo.id),
            "filename": photo.filename,
            "original_name": photo.original_name,
            "width": photo.width,
            "height": photo.height,
            "photo_time": photo.photo_time,
            "upload_time": photo.upload_time,
            "file_type": photo.file_type.value if hasattr(photo.file_type, 'value') else str(photo.file_type),
            "file_size": photo.file_size,
            "is_deleted": photo.is_deleted,
            "deleted_at": photo.deleted_at,
            "tags": tags,
            "quality_score": quality_score,
        })
    
    return BaseResponse(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    })


@router.post("/{album_id}/photos/{photo_id}", response_model=BaseResponse)
def add_photo_to_album(
    album_id: str,
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    将照片添加到相册
    """
    try:
        album_uuid = uuid.UUID(album_id)
        photo_uuid = uuid.UUID(photo_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的ID")
    
    album = album_crud.get_album_by_id(db, album_uuid)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    
    if album.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此相册")
    
    photo = photo_crud.get_photo_by_id(db, photo_uuid)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    success = album_crud.add_photo_to_album(db, album_uuid, photo_uuid)
    if not success:
        raise HTTPException(status_code=500, detail="添加照片失败")
    
    return BaseResponse(msg="照片已添加到相册")


@router.delete("/{album_id}/photos/{photo_id}", response_model=BaseResponse)
def remove_photo_from_album(
    album_id: str,
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    从相册中移除照片
    """
    try:
        album_uuid = uuid.UUID(album_id)
        photo_uuid = uuid.UUID(photo_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的ID")
    
    album = album_crud.get_album_by_id(db, album_uuid)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    
    if album.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此相册")
    
    success = album_crud.remove_photo_from_album(db, album_uuid, photo_uuid)
    if not success:
        raise HTTPException(status_code=500, detail="移除照片失败")
    
    return BaseResponse(msg="照片已从相册移除")
