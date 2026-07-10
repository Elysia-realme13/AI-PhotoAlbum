"""
人脸相关 Schema
"""
import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, field_validator


class FaceIdentityResponse(BaseModel):
    """人脸身份响应"""
    id: str
    owner_id: str
    identity_name: str
    description: Optional[str] = None
    default_face_id: Optional[int] = None
    is_hidden: bool = False
    face_count: int = 0
    created_at: datetime

    @field_validator("id", "owner_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class FaceIdentityUpdate(BaseModel):
    """更新人脸身份"""
    identity_name: Optional[str] = None
    description: Optional[str] = None
    is_hidden: Optional[bool] = None


class FaceResponse(BaseModel):
    """人脸检测结果响应"""
    id: int
    photo_id: str
    face_identity_id: Optional[str] = None
    face_rect: Optional[list] = None
    confidence: Optional[float] = None

    model_config = {"from_attributes": True}


class FaceMergeRequest(BaseModel):
    """合并人脸请求"""
    source_ids: list  # 要合并到 target_id 的 identity_id 列表
    target_id: str    # 目标 identity_id
