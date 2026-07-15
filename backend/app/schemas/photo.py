"""
照片相关 Schema — API 层使用的请求/响应模型

分层说明:
    - 项目现有 app/schemas/photo.py 定义的是 ORM → JSON 的基础模型
    - 本文件在此基础上扩展 API 层专用的请求体和嵌套响应
"""

import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ── 请求体 ────────────────────────────────────────

class PhotoUpdateRequest(BaseModel):
    """修改照片属性（如修正拍摄时间）"""
    photo_time: Optional[datetime] = None
    original_name: Optional[str] = Field(None, max_length=255)


class ReanalyzeRequest(BaseModel):
    """重新 AI 分析请求"""
    tasks: list[str] = Field(
        ..., min_length=1,
        description="要重新分析的任务类型，如 ['face_detect', 'image_description']"
    )


class BatchPhotoRequest(BaseModel):
    """批量操作请求"""
    photo_ids: list[str] = Field(..., min_length=1, max_length=500)


class PhotoListParams(BaseModel):
    """照片列表查询参数（非请求体，用于 Query 参数验证）"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    sort_by: str = Field(default="photo_time", pattern="^(photo_time|upload_time|file_name|file_size)$")
    order: str = Field(default="desc", pattern="^(asc|desc)$")
    file_type: Optional[str] = Field(default=None, pattern="^(image|video|live_photo)$")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    album_id: Optional[str] = None
    is_deleted: bool = False


# ── 响应体（扩展现有 Schema）──────────────────────

class PhotoMetadataResponse(BaseModel):
    """EXIF 元数据"""
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

    model_config = {"from_attributes": True}


class PhotoDescriptionResponse(BaseModel):
    """AI 描述"""
    description: Optional[str] = None
    narrative: Optional[str] = None
    tags: Optional[list] = None
    quality_score: Optional[float] = None
    memory_score: Optional[float] = None

    model_config = {"from_attributes": True}


class FaceBoxResponse(BaseModel):
    """照片上的人脸框（简要版，不含完整特征向量）"""
    id: int
    face_identity_id: Optional[str] = None
    identity_name: Optional[str] = None
    face_rect: Optional[list] = None
    confidence: Optional[float] = None

    model_config = {"from_attributes": True}

    @field_validator("face_identity_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v


class PhotoDetailResponse(BaseModel):
    """照片详情 = 基础信息 + 元数据 + 描述 + 人脸"""
    # 基础信息（来自 Photo）
    id: str
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

    # 嵌套关联
    metadata: Optional[PhotoMetadataResponse] = None
    description: Optional[PhotoDescriptionResponse] = None
    faces: list[FaceBoxResponse] = []

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> str:
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class PhotoListItem(BaseModel):
    """照片列表项（缩略版，不含嵌套数据以减少传输量）"""
    id: str
    filename: str
    original_name: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    photo_time: Optional[datetime] = None
    upload_time: Optional[datetime] = None
    file_type: str = "image"
    file_size: Optional[int] = None
    is_deleted: bool = False
    # 列表中也带简要的描述信息，方便前端展示标签
    tags: Optional[list] = None
    quality_score: Optional[float] = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> str:
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class UploadResult(BaseModel):
    """单张照片上传结果"""
    photo: PhotoListItem
    task_ids: list[str] = []


class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    photos: list[UploadResult] = []
    total_uploaded: int = 0
    total_skipped: int = 0  # MD5 重复跳过的数量
    skipped_md5: list[str] = []  # 跳过的 MD5 列表


class TimelineGroup(BaseModel):
    """时间轴分组"""
    date: str  # "2025-07" 或 "2025-07-14" 取决于 group_by
    count: int
    cover_photo: Optional[PhotoListItem] = None


class MapPhotoItem(BaseModel):
    """地图视图照片项"""
    id: str
    latitude: float
    longitude: float
    photo_time: Optional[datetime] = None
    thumbnail_url: Optional[str] = None  # TODO: Phase 2 后续实现缩略图

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> str:
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}
