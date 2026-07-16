"""
认证 API 路由
注册 / 登录 / 获取当前用户
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate, ChangePasswordRequest, TokenResponse
from app.crud.user import create_user, authenticate_user, get_user_by_username, get_user_by_email, update_user
from app.core.security import create_access_token, hash_password, verify_password
from app.api.deps import get_current_user
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


@router.patch("/me", response_model=UserResponse)
def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户个人资料"""
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_user(db, current_user, **update_data)
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户密码"""
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "密码已修改"}
