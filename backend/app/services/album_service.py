"""
智能相册聚合服务

把 albums.conditions(JSON) 解析为实时照片查询。smart/conditional 相册的照片
与计数均由此动态解析，不物化到 album_photos，因此随标签/地理编码/人物聚类变化
自动更新。

conditions 结构:
    {
        "date_from": "2024-01-01",   # 拍摄时间下界（含）
        "date_to":   "2024-12-31",   # 拍摄时间上界（含）
        "province":  "浙江省",        # 省份精确匹配
        "city":      "杭州市",        # 城市精确匹配
        "tags":      ["cat", "dog"], # 任意命中即可
        "face_identity_id": "<uuid>",# 该人物出现的照片
        "match":     "all"           # all=各组 AND(默认); any=各组 OR
    }
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.description import PhotoTag, PhotoTagRelation
from app.models.face import Face
from app.models.photo import Photo, PhotoMetadata


def _parse_date(value) -> Optional[datetime]:
    """接受 'YYYY-MM-DD' / ISO 字符串 / datetime，无效返回 None"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def build_smart_filters(conditions: Optional[dict]) -> List:
    """
    把 conditions 转为 SQLAlchemy 过滤表达式列表（纯函数，便于单测）。

    注意：province/city 引用 PhotoMetadata 列，调用方需在存在这些条件时
    join PhotoMetadata（见 _needs_metadata_join / _base_query）。
    """
    conditions = conditions or {}
    filters: List = []

    date_from = _parse_date(conditions.get("date_from"))
    if date_from:
        filters.append(Photo.photo_time >= date_from)

    date_to = _parse_date(conditions.get("date_to"))
    if date_to:
        filters.append(Photo.photo_time <= date_to)

    province = conditions.get("province")
    if province:
        filters.append(PhotoMetadata.province == province)

    city = conditions.get("city")
    if city:
        filters.append(PhotoMetadata.city == city)

    tags = conditions.get("tags")
    if tags:
        tag_sub = (
            select(PhotoTagRelation.photo_id)
            .join(PhotoTag, PhotoTag.id == PhotoTagRelation.tag_id)
            .where(PhotoTag.tag_name.in_(tags))
        )
        filters.append(Photo.id.in_(tag_sub))

    face_identity_id = conditions.get("face_identity_id")
    if face_identity_id:
        face_sub = select(Face.photo_id).where(Face.face_identity_id == face_identity_id)
        filters.append(Photo.id.in_(face_sub))

    return filters


def _needs_metadata_join(conditions: Optional[dict]) -> bool:
    conditions = conditions or {}
    return bool(conditions.get("province") or conditions.get("city"))


def _base_query(db: Session, owner_id, conditions: Optional[dict]):
    conditions = conditions or {}
    query = db.query(Photo).filter(
        Photo.owner_id == owner_id,
        Photo.is_deleted.is_(False),
    )
    if _needs_metadata_join(conditions):
        query = query.join(PhotoMetadata, PhotoMetadata.photo_id == Photo.id)

    filters = build_smart_filters(conditions)
    if filters:
        match = str(conditions.get("match") or "all").lower()
        combiner = or_ if match == "any" else and_
        query = query.filter(combiner(*filters))
    return query


def resolve_smart_album(
    db: Session, owner_id, conditions: Optional[dict], page: int = 1, page_size: int = 50
) -> Tuple[int, list]:
    """动态解析智能相册照片（分页）"""
    query = _base_query(db, owner_id, conditions)
    total = query.count()
    photos = (
        query.order_by(Photo.photo_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return total, photos


def count_smart_album(db: Session, owner_id, conditions: Optional[dict]) -> int:
    """动态解析智能相册照片数量"""
    return _base_query(db, owner_id, conditions).count()


__all__ = ["build_smart_filters", "resolve_smart_album", "count_smart_album"]
