"""
认证 API 路由
注册 / 登录 / 获取当前用户 / 更新资料 / 修改密码
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session
import uuid
import aiofiles
from app.database.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.crud.user import create_user, authenticate_user, get_user_by_username, get_user_by_email, update_user
from app.core.security import create_access_token, hash_password, verify_password
from app.api.deps import get_current_user, get_required_user
from app.models.user import User
from app.config.settings import settings
from app.services.captcha_service import generate_captcha, verify_captcha

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


class CaptchaResponse(BaseModel):
    captcha_id: str
    captcha_image: str


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha():
    """获取登录验证码"""
    captcha_id, captcha_image = generate_captcha()
    return CaptchaResponse(captcha_id=captcha_id, captcha_image=captcha_image)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    # 验证码校验
    if not verify_captcha(data.captcha_id or "", data.captcha_code or ""):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

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
    # 所有失败情况返回统一错误，防止被当作密码验证机
    # 先检查格式（快速拒绝，不涉及密码比对，无安全风险）
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="操作失败，请重试")
    # 再验证旧密码哈希
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="操作失败，请重试")
    # 最后比对新旧密码
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="操作失败，请重试")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "密码已修改"}


ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """上传头像图片，返回头像 URL"""
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WebP/GIF 格式")

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="头像文件不能超过 5MB")

    # 保存到头像目录
    avatar_dir = Path(settings.AVATAR_DIR)
    avatar_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "avatar.jpg").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = avatar_dir / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # 删除旧头像文件
    if current_user.avatar_url:
        old_name = current_user.avatar_url.rsplit("/", 1)[-1]
        old_path = avatar_dir / old_name
        if old_path.exists():
            old_path.unlink()

    # 更新数据库
    avatar_url = f"/api/avatars/{filename}"
    update_user(db, current_user, avatar_url=avatar_url)

    return {"avatar_url": avatar_url}
