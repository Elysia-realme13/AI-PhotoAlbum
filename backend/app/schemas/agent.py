"""
Agent 对话相关 Schema
"""
import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AgentSessionCreate(BaseModel):
    """创建对话会话"""
    title: Optional[str] = Field(None, max_length=200)


class AgentSessionResponse(BaseModel):
    """对话会话响应"""
    id: str
    user_id: str
    title: Optional[str] = None
    status: str
    message_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class AgentMessageResponse(BaseModel):
    """对话消息响应"""
    id: int
    session_id: str
    role: str
    content: str
    tool_calls: Optional[list] = None
    created_at: datetime

    @field_validator("session_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    """Agent 聊天请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    connection_id: Optional[str] = None
    model_name: Optional[str] = None
