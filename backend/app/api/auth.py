"""
认证 API 路由
注册 / 登录 / 获取当前用户 / 更新资料 / 修改密码
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.crud.user import create_user, authenticate_user, get_user_by_username, get_user_by_email, update_user
from app.core.security import create_access_token, hash_password, verify_password
from app.api.deps import get_current_user, get_required_user
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    if get_user_by_username(db, data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = create_user(
        db,
        username=data.username,
        email=data.email,
        password=data.password,
        nickname=data.nickname,
    )

    # 生成 Token
    token = create_access_token(data={"sub": str(user.id), "username": user.username})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_access_token(data={"sub": str(user.id), "username": user.username})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    return UserResponse.model_validate(current_user)


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.patch("/me", response_model=UserResponse)
def update_profile(
    data: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """更新当前用户资料（昵称、头像）"""
    update_kwargs = {}
    if data.nickname is not None:
        update_kwargs["nickname"] = data.nickname
    if data.avatar_url is not None:
        update_kwargs["avatar_url"] = data.avatar_url
    if update_kwargs:
        current_user = update_user(db, current_user, **update_kwargs)
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """修改当前用户密码"""
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "密码已修改"}
