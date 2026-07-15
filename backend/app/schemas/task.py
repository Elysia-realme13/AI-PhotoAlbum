"""
任务相关 Schema
"""

import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    photo_id: Optional[str] = None
    task_type: str
    status: str
    progress: Optional[dict] = {}
    result: Optional[dict] = {}
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("id", "photo_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class TaskStatsResponse(BaseModel):
    """任务统计"""
    total: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
