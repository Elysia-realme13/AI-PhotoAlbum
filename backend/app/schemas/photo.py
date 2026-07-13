"""
照片相关 Schema
"""
import uuid
from typing import Optional, Any, List
from datetime import datetime
from pydantic import BaseModel, field_validator


class PhotoResponse(BaseModel):
    """照片响应"""
    id: str
    owner_id: Optional[str] = None
    filename: str
    original_name: Optional[str] = None
    file_path: str
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    photo_time: Optional[datetime] = None
    upload_time: Optional[datetime] = None
    file_type: str = "image"
    md5: Optional[str] = None
    is_deleted: bool = False
    processed_tasks: Optional[dict] = {}

    @field_validator("id", "owner_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class PhotoListResponse(BaseModel):
    """照片列表响应"""
    total: int
    page: int
    page_size: int
    items: List[PhotoResponse]


class PhotoMetadataResponse(BaseModel):
    """EXIF 元数据响应"""
    id: Optional[str] = None
    photo_id: Optional[str] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    focal_length: Optional[float] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[str] = None
    iso: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    country: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None

    @field_validator("id", "photo_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class PhotoDescriptionResponse(BaseModel):
    """AI 描述响应"""
    id: str
    photo_id: str
    description: Optional[str] = None
    narrative: Optional[str] = None
    tags: Optional[list] = None
    quality_score: Optional[float] = None
    memory_score: Optional[float] = None

    @field_validator("id", "photo_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class PhotoDetailResponse(PhotoResponse):
    """照片详情响应（含元数据）"""
    metadata: Optional[PhotoMetadataResponse] = None
