"""
照片 CRUD 操作

负责所有照片相关的数据库查询和写入。
不包含业务逻辑（如文件存储、EXIF 解析）——这些属于 Service 层。
"""

import uuid
import hashlib
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import and_, or_, desc, asc, func
from app.models.photo import Photo, PhotoMetadata
from app.models.description import ImageDescription, PhotoTag, PhotoTagRelation
from app.models.face import Face, FaceIdentity


# ── 创建 ──────────────────────────────────────────

def create_photo(
    db: Session,
    owner_id: uuid.UUID,
    filename: str,
    original_name: str,
    file_path: str,
    file_size: int,
    md5: str,
    file_type: str = "image",
    width: Optional[int] = None,
    height: Optional[int] = None,
    photo_time: Optional[datetime] = None,
) -> Photo:
    """创建照片记录"""
    photo = Photo(
        owner_id=owner_id,
        filename=filename,
        original_name=original_name,
        file_path=file_path,
        file_size=file_size,
        md5=md5,
        file_type=file_type,
        width=width,
        height=height,
        photo_time=photo_time or datetime.now(),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def create_photo_metadata(
    db: Session,
    photo_id: uuid.UUID,
    **kwargs
) -> PhotoMetadata:
    """创建或更新 EXIF 元数据"""
    metadata = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == photo_id).first()
    if metadata:
        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
    else:
        metadata = PhotoMetadata(photo_id=photo_id, **kwargs)
        db.add(metadata)
    db.commit()
    db.refresh(metadata)
    return metadata


# ── 查询 ──────────────────────────────────────────

def get_photo_by_id(
    db: Session,
    photo_id: uuid.UUID,
    owner_id: Optional[uuid.UUID] = None,
    include_deleted: bool = False,
) -> Optional[Photo]:
    """获取单张照片，可选所有者校验"""
    query = db.query(Photo).filter(Photo.id == photo_id)
    if owner_id:
        query = query.filter(Photo.owner_id == owner_id)
    if not include_deleted:
        query = query.filter(Photo.is_deleted == False)
    return query.first()


def get_photo_detail(
    db: Session,
    photo_id: uuid.UUID,
    owner_id: Optional[uuid.UUID] = None,
) -> Optional[Photo]:
    """获取照片详情（含元数据、描述、人脸）"""
    query = db.query(Photo).options(
        joinedload(Photo.metadata_info),
        joinedload(Photo.image_description),
        joinedload(Photo.faces).joinedload(Face.identity),
    ).filter(Photo.id == photo_id)
    if owner_id:
        query = query.filter(Photo.owner_id == owner_id)
    return query.first()


def get_photos_by_md5(db: Session, md5: str) -> Optional[Photo]:
    """通过 MD5 查找已存在的照片（去重用）"""
    return db.query(Photo).filter(Photo.md5 == md5, Photo.is_deleted == False).first()


def get_photo_list(
    db: Session,
    owner_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "photo_time",
    order: str = "desc",
    file_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    album_id: Optional[uuid.UUID] = None,
    is_deleted: bool = False,
) -> Tuple[List[Photo], int]:
    """
    照片列表（分页 + 多维度筛选）

    Returns:
        (photos, total_count)
    """
    query = db.query(Photo).filter(
        Photo.owner_id == owner_id,
        Photo.is_deleted == is_deleted,
    )

    # 可选筛选条件
    if file_type:
        query = query.filter(Photo.file_type == file_type)
    if date_from:
        query = query.filter(Photo.photo_time >= date_from)
    if date_to:
        query = query.filter(Photo.photo_time <= date_to)
    if album_id:
        from app.models.album import AlbumPhoto
        query = query.join(AlbumPhoto, AlbumPhoto.photo_id == Photo.id).filter(
            AlbumPhoto.album_id == album_id
        )

    # 排序
    sort_column = getattr(Photo, sort_by, Photo.photo_time)
    if order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    photos = query.offset(offset).limit(page_size).all()

    return photos, total


def get_photos_by_ids(
    db: Session,
    photo_ids: List[uuid.UUID],
    owner_id: Optional[uuid.UUID] = None,
) -> List[Photo]:
    """批量获取照片"""
    query = db.query(Photo).filter(Photo.id.in_(photo_ids))
    if owner_id:
        query = query.filter(Photo.owner_id == owner_id)
    return query.all()


# ── 更新 ──────────────────────────────────────────

def update_photo(
    db: Session,
    photo: Photo,
    **kwargs
) -> Photo:
    """更新照片属性"""
    for key, value in kwargs.items():
        if value is not None and hasattr(photo, key):
            setattr(photo, key, value)
    db.commit()
    db.refresh(photo)
    return photo


def soft_delete_photo(db: Session, photo: Photo) -> Photo:
    """软删除（移到回收站）"""
    photo.is_deleted = True
    photo.deleted_at = datetime.now()
    db.commit()
    db.refresh(photo)
    return photo


def restore_photo(db: Session, photo: Photo) -> Photo:
    """从回收站恢复"""
    photo.is_deleted = False
    photo.deleted_at = None
    db.commit()
    db.refresh(photo)
    return photo


def batch_soft_delete(
    db: Session,
    photo_ids: List[uuid.UUID],
    owner_id: uuid.UUID,
) -> Tuple[int, int]:
    """批量软删除（移到回收站）"""
    now = datetime.now()
    photos = (
        db.query(Photo)
        .filter(Photo.id.in_(photo_ids), Photo.owner_id == owner_id, ~Photo.is_deleted)
        .all()
    )
    for photo in photos:
        photo.is_deleted = True
        photo.deleted_at = now
    db.commit()
    return len(photos), len(photo_ids) - len(photos)


def batch_restore(
    db: Session,
    photo_ids: List[uuid.UUID],
    owner_id: uuid.UUID,
) -> Tuple[int, int]:
    """批量恢复（从回收站恢复）"""
    photos = (
        db.query(Photo)
        .filter(Photo.id.in_(photo_ids), Photo.owner_id == owner_id, Photo.is_deleted)
        .all()
    )
    for photo in photos:
        photo.is_deleted = False
        photo.deleted_at = None
    db.commit()
    return len(photos), len(photo_ids) - len(photos)


def batch_permanent_delete(
    db: Session,
    photo_ids: List[uuid.UUID],
    owner_id: uuid.UUID,
) -> Tuple[int, int]:
    """
    批量永久删除（数据库记录）

    Returns:
        (success_count, fail_count)
    """
    photos = (
        db.query(Photo)
        .filter(Photo.id.in_(photo_ids), Photo.owner_id == owner_id, Photo.is_deleted)
        .all()
    )
    for photo in photos:
        db.delete(photo)
    db.commit()
    return len(photos), len(photo_ids) - len(photos)


def get_deleted_photo_file_paths(
    db: Session,
    photo_ids: List[uuid.UUID],
    owner_id: uuid.UUID,
) -> List[str]:
    """获取回收站中照片的文件路径（用于永久删除前清理文件）"""
    photos = (
        db.query(Photo.file_path)
        .filter(Photo.id.in_(photo_ids), Photo.owner_id == owner_id, Photo.is_deleted)
        .all()
    )
    return [p.file_path for p in photos if p.file_path]


def permanent_delete_photo(db: Session, photo: Photo):
    """物理删除（数据库记录 + 文件由 Service 层处理）"""
    db.delete(photo)
    db.commit()


def get_deleted_photos(db: Session, owner_id: str) -> List[Photo]:
    """获取回收站中的照片列表"""
    return (
        db.query(Photo)
        .filter(
            Photo.owner_id == uuid.UUID(owner_id),
            Photo.is_deleted,
        )
        .order_by(desc(Photo.deleted_at))
        .all()
    )


def get_photo_by_id_any(db: Session, photo_id: str) -> Optional[Photo]:
    """获取任意照片（含已删除，不做权限校验）"""
    return db.query(Photo).filter(Photo.id == photo_id).first()


def update_processed_tasks(
    db: Session,
    photo: Photo,
    task_type: str,
    result: dict,
) -> Photo:
    """更新照片的已完成任务标记"""
    tasks = dict(photo.processed_tasks or {})
    tasks[task_type] = result
    photo.processed_tasks = tasks
    db.commit()
    db.refresh(photo)
    return photo


# ── 统计查询 ──────────────────────────────────────

def get_timeline_groups(
    db: Session,
    owner_id: uuid.UUID,
    group_by: str = "month",
) -> List[dict]:
    """时间轴分组统计"""
    if group_by == "year":
        date_format = func.to_char(Photo.photo_time, "YYYY")
    elif group_by == "day":
        date_format = func.to_char(Photo.photo_time, "YYYY-MM-DD")
    else:  # month
        date_format = func.to_char(Photo.photo_time, "YYYY-MM")

    results = (
        db.query(
            date_format.label("date"),
            func.count(Photo.id).label("count"),
            func.array_agg(Photo.id).label("photo_ids"),
        )
        .filter(Photo.owner_id == owner_id, Photo.is_deleted == False)
        .group_by("date")
        .order_by(desc("date"))
        .all()
    )
    return [{"date": r.date, "count": r.count, "cover_photo_id": (r.photo_ids or [None])[0]} for r in results]


def get_map_photos(
    db: Session,
    owner_id: uuid.UUID,
    sw_lat: Optional[float] = None,
    sw_lng: Optional[float] = None,
    ne_lat: Optional[float] = None,
    ne_lng: Optional[float] = None,
) -> List[Photo]:
    """获取有 GPS 坐标的照片（可选视口范围过滤）"""
    query = (
        db.query(Photo)
        .join(PhotoMetadata, PhotoMetadata.photo_id == Photo.id)
        .filter(
            Photo.owner_id == owner_id,
            Photo.is_deleted == False,
            PhotoMetadata.latitude.isnot(None),
            PhotoMetadata.longitude.isnot(None),
        )
    )
    if sw_lat and sw_lng and ne_lat and ne_lng:
        query = query.filter(
            and_(
                PhotoMetadata.latitude >= sw_lat,
                PhotoMetadata.latitude <= ne_lat,
                PhotoMetadata.longitude >= sw_lng,
                PhotoMetadata.longitude <= ne_lng,
            )
        )
    return query.limit(500).all()


# ── 统计 ──────────────────────────────────────────

def get_user_photo_count(db: Session, owner_id: uuid.UUID) -> int:
    """用户照片总数（不含已删除）"""
    return (
        db.query(func.count(Photo.id))
        .filter(Photo.owner_id == owner_id, Photo.is_deleted == False)
        .scalar()
    )


def get_storage_used(db: Session, owner_id: uuid.UUID) -> int:
    """用户存储空间使用量（字节）"""
    result = (
        db.query(func.sum(Photo.file_size))
        .filter(Photo.owner_id == owner_id, Photo.is_deleted == False)
        .scalar()
    )
    return result or 0
