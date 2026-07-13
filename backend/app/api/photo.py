"""
照片 API 路由
上传 / 列表 / 详情 / 删除 / 恢复 / 元数据
"""
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.storage import storage
from app.api.deps import get_required_user
from app.models.user import User
from app.models.photo import Photo
from app.crud.photo import (
    create_photo,
    get_photo_by_id,
    get_photo_by_id_any,
    get_photos_by_owner,
    soft_delete_photo,
    restore_photo,
    create_metadata,
    get_metadata,
)
from app.schemas.photo import (
    PhotoResponse,
    PhotoListResponse,
    PhotoMetadataResponse,
    PhotoDetailResponse,
)
from app.services.thumbnail import generate_thumbnail_bytes
from app.services.exif_service import extract_exif

router = APIRouter(prefix="/api/photos", tags=["照片"])


@router.post("/upload", response_model=PhotoDetailResponse)
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """上传照片"""
    # 验证文件类型
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif', '.bmp'}
    original_name = file.filename or "unknown"
    ext = original_name.lower().rsplit('.', 1)[-1] if '.' in original_name else ''
    if f'.{ext}' not in allowed_extensions and ext:
        raise HTTPException(400, f"不支持的文件格式: .{ext}")

    # 读取文件内容
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "文件为空")

    # 生成唯一文件名
    import uuid as _uuid
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else 'jpg'
    filename = f"{_uuid.uuid4().hex}.{ext}"

    # 保存原始文件
    filename, file_path, file_size = await storage.save_upload_bytes(filename, file_bytes)

    # 提取 EXIF 信息
    from pathlib import Path
    exif_data = extract_exif(str(Path(file_path)))

    # 生成缩略图
    try:
        thumb_bytes = generate_thumbnail_bytes(file_bytes)
        await storage.save_thumbnail(filename, thumb_bytes)
    except Exception:
        thumb_bytes = None  # 缩略图生成失败不阻塞上传

    # 计算 MD5
    md5_hash = hashlib.md5(file_bytes).hexdigest()

    # 创建数据库记录
    photo = create_photo(
        db=db,
        owner_id=str(current_user.id),
        filename=filename,
        original_name=original_name,
        file_path=file_path,
        file_size=file_size,
        width=exif_data.get('width') or 0,
        height=exif_data.get('height') or 0,
        photo_time=exif_data.get('photo_time') or datetime.now(),
        md5=md5_hash,
    )

    # 保存 EXIF 元数据（排除 width/height/photo_time 等 Photo 表自有字段）
    metadata_fields = {
        'camera_make', 'camera_model', 'lens_model',
        'focal_length', 'aperture', 'shutter_speed', 'iso',
        'latitude', 'longitude', 'altitude',
    }
    metadata_dict = {k: v for k, v in exif_data.items() if k in metadata_fields and v is not None}
    metadata = create_metadata(db, str(photo.id), metadata_dict)

    return PhotoDetailResponse(
        id=str(photo.id),
        owner_id=str(photo.owner_id),
        filename=photo.filename,
        original_name=photo.original_name,
        file_path=photo.file_path,
        file_size=photo.file_size,
        width=photo.width,
        height=photo.height,
        photo_time=photo.photo_time,
        upload_time=photo.upload_time,
        file_type=photo.file_type.value if photo.file_type else "image",
        md5=photo.md5,
        metadata=PhotoMetadataResponse.model_validate(metadata) if metadata else None,
    )


@router.get("", response_model=PhotoListResponse)
def list_photos(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("photo_time", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """照片列表（分页）"""
    photos, total = get_photos_by_owner(
        db=db,
        owner_id=str(current_user.id),
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items = [PhotoResponse.model_validate(p) for p in photos]
    return PhotoListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{photo_id}", response_model=PhotoDetailResponse)
def get_photo_detail(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """照片详情（含元数据）"""
    photo = get_photo_by_id(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    if str(photo.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权访问此照片")

    metadata = get_metadata(db, photo_id)

    return PhotoDetailResponse(
        id=str(photo.id),
        owner_id=str(photo.owner_id),
        filename=photo.filename,
        original_name=photo.original_name,
        file_path=photo.file_path,
        file_size=photo.file_size,
        width=photo.width,
        height=photo.height,
        photo_time=photo.photo_time,
        upload_time=photo.upload_time,
        file_type=photo.file_type.value if photo.file_type else "image",
        md5=photo.md5,
        is_deleted=photo.is_deleted,
        processed_tasks=photo.processed_tasks,
        metadata=PhotoMetadataResponse.model_validate(metadata) if metadata else None,
    )


@router.delete("/{photo_id}")
def delete_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """软删除照片（移入回收站）"""
    photo = get_photo_by_id(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    if str(photo.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权删除此照片")

    soft_delete_photo(db, photo)
    return {"message": "已移入回收站", "photo_id": photo_id}


@router.post("/{photo_id}/restore")
def restore_photo_endpoint(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """从回收站恢复照片"""
    photo = get_photo_by_id_any(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    if str(photo.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权操作此照片")

    if not photo.is_deleted:
        raise HTTPException(400, "照片未在回收站中")

    restore_photo(db, photo)
    return {"message": "已恢复", "photo_id": photo_id}


@router.get("/{photo_id}/metadata", response_model=PhotoMetadataResponse)
def get_photo_metadata(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取照片 EXIF 元数据"""
    photo = get_photo_by_id(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    if str(photo.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权访问此照片")

    metadata = get_metadata(db, photo_id)
    if not metadata:
        raise HTTPException(404, "暂无元数据")

    return PhotoMetadataResponse.model_validate(metadata)
