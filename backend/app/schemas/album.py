"""
相册相关 Schema
"""
import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AlbumCreate(BaseModel):
    """创建相册"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    album_type: str = "manual"
    conditions: Optional[dict] = None


class AlbumUpdate(BaseModel):
    """更新相册"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    cover_photo_id: Optional[str] = None


class AlbumResponse(BaseModel):
    """相册响应"""
    id: str
    owner_id: str
    name: str
    description: Optional[str] = None
    cover_photo_id: Optional[str] = None
    is_system: bool = False
    album_type: str = "manual"
    conditions: Optional[dict] = None
    photo_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("id", "owner_id", "cover_photo_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}
