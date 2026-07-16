"""
用户相关 Schema
"""
import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """用户注册"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    nickname: Optional[str] = Field(None, max_length=50)


class UserLogin(BaseModel):
    """用户登录"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    email: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid_to_str(cls, v: Any) -> str:
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """用户信息更新"""
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """修改密码"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
