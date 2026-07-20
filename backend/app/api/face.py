"""
Face API — identity CRUD and clustering
GET   /api/faces/identities            — list all identities
GET   /api/faces/identities/{id}/photos — identity photos
PUT   /api/faces/identities/{id}       — update identity
POST  /api/faces/identities/merge      — merge identities
POST  /api/faces/identities/name       — bind name (agent confirmation)
"""
import uuid as _uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.models.face import Face, FaceIdentity
from app.services.face_cluster_service import get_representative_faces, get_cluster_face_photos
from app.services.name_confirmation_service import confirm_name, find_clusters_by_name
from app.schemas.response import BaseResponse

router = APIRouter(prefix="/api/faces/identities", tags=["faces"])


# ── Pydantic models ───────────────────────────────────────

class FaceIdentityUpdate(BaseModel):
    identity_name: Optional[str] = None
    description: Optional[str] = None
    is_hidden: Optional[bool] = None


class NameBindRequest(BaseModel):
    cluster_id: str
    name: str
    aliases: Optional[List[str]] = None
    session_id: Optional[str] = None
    query: Optional[str] = None


class MergeRequest(BaseModel):
    source_ids: List[str]
    target_id: str


class IdentityResponse(BaseModel):
    id: str
    identity_name: Optional[str] = None
    description: Optional[str] = None
    face_count: int
    representative_faces: List[dict] = []
    is_hidden: bool = False

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────

def _get_identity_or_404(db: Session, identity_id: str, owner_id: str) -> FaceIdentity:
    try:
        iid = _uuid.UUID(identity_id)
    except ValueError:
        raise HTTPException(400, "无效的身份ID")
    identity = db.query(FaceIdentity).filter(
        FaceIdentity.id == iid,
        FaceIdentity.owner_id == _uuid.UUID(owner_id),
    ).first()
    if not identity:
        raise HTTPException(404, "身份不存在")
    return identity


# ── GET / — 列出所有 identities ────────────────────────────

@router.get("")
def list_identities(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """返回当前用户的所有人脸身份（含命名和未命名）"""
    owner_uuid = _uuid.UUID(str(current_user.id))
    query = (
        db.query(
            FaceIdentity,
            func.count(Face.photo_id.distinct()).label("face_count"),
        )
        .outerjoin(Face, Face.face_identity_id == FaceIdentity.id)
        .filter(
            FaceIdentity.owner_id == owner_uuid,
            FaceIdentity.is_hidden == False,
        )
    )
    if q:
        query = query.filter(FaceIdentity.identity_name.ilike(f"%{q}%"))
    rows = (
        query
        .group_by(FaceIdentity.id)
        .order_by(
            FaceIdentity.identity_name.is_(None).asc(),
            func.count(Face.photo_id.distinct()).desc(),
        )
        .all()
    )

    result = []
    for identity, face_count in rows:
        reps = get_representative_faces(db, identity.id, top_k=3)
        cover_photo_id = reps[0]["photo_id"] if reps else None
        result.append({
            "id": str(identity.id),
            "identity_id": str(identity.id),
            "identity_name": identity.identity_name,
            "description": identity.description,
            "face_count": face_count,
            "cover_photo_id": cover_photo_id,
            "representative_faces": reps,
            "is_hidden": identity.is_hidden,
        })
    return result


# ── GET /{identity_id}/photos ──────────────────────────────

@router.get("/{identity_id}/photos")
def identity_photos(
    identity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """返回指定身份下的所有照片"""
    identity = _get_identity_or_404(db, identity_id, str(current_user.id))
    photo_ids = get_cluster_face_photos(db, identity.id)

    if not photo_ids:
        return []

    from app.models.photo import Photo
    from app.schemas.photo import PhotoListResponse

    photos = (
        db.query(Photo)
        .filter(Photo.id.in_([_uuid.UUID(pid) for pid in photo_ids]))
        .order_by(Photo.photo_time.desc())
        .all()
    )
    return [
        {
            "id": str(p.id),
            "filename": p.filename,
            "original_name": p.original_name,
            "file_type": p.file_type,
            "file_size": p.file_size,
            "photo_time": str(p.photo_time) if p.photo_time else None,
            "upload_time": str(p.upload_time) if p.upload_time else None,
            "is_deleted": p.is_deleted,
        }
        for p in photos
    ]


# ── PUT /{identity_id} ────────────────────────────────────

@router.put("/{identity_id}")
def update_identity(
    identity_id: str,
    data: FaceIdentityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """更新身份信息（名称、描述、隐藏状态）"""
    identity = _get_identity_or_404(db, identity_id, str(current_user.id))

    if data.identity_name is not None:
        identity.identity_name = data.identity_name
    if data.description is not None:
        identity.description = data.description
    if data.is_hidden is not None:
        identity.is_hidden = data.is_hidden

    db.commit()
    db.refresh(identity)
    return {
        "id": str(identity.id),
        "identity_name": identity.identity_name,
        "description": identity.description,
        "is_hidden": identity.is_hidden,
    }


# ── POST /merge ───────────────────────────────────────────

@router.post("/merge")
def merge_identities(
    req: MergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """将多个来源身份合并到目标身份"""
    try:
        tgt = _uuid.UUID(req.target_id)
    except ValueError:
        raise HTTPException(400, "无效的目标ID")

    target = db.query(FaceIdentity).filter(FaceIdentity.id == tgt).first()
    if not target:
        raise HTTPException(404, "目标身份不存在")

    merged_count = 0
    for sid in req.source_ids:
        try:
            src = _uuid.UUID(sid)
        except ValueError:
            continue
        if src == tgt:
            continue
        source = db.query(FaceIdentity).filter(FaceIdentity.id == src).first()
        if not source:
            continue
        # 迁移所有人脸到目标身份
        db.query(Face).filter(Face.face_identity_id == src).update(
            {"face_identity_id": tgt}
        )
        source.is_hidden = True
        merged_count += 1

    db.commit()
    return {
        "message": f"已合并 {merged_count} 个身份",
        "target_id": req.target_id,
        "merged_count": merged_count,
    }


# ── POST /name — 绑定名称（agent 确认流程）────────────────

@router.post("/name")
def bind_name(
    req: NameBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """绑定身份名称（支持 agent 会话确认流程）"""
    if req.session_id and req.query:
        success = confirm_name(
            db=db, session_id=req.session_id, query=req.query,
            cluster_id=req.cluster_id, name=req.name, aliases=req.aliases,
        )
        if not success:
            raise HTTPException(400, "名称确认失败：pending 会话已过期")
        return {"message": "name confirmed", "cluster_id": req.cluster_id, "name": req.name}

    try:
        cid = _uuid.UUID(req.cluster_id)
    except ValueError:
        raise HTTPException(400, "无效的聚类ID")

    identity = db.query(FaceIdentity).filter(FaceIdentity.id == cid).first()
    if not identity:
        raise HTTPException(404, "聚类不存在")

    identity.identity_name = req.name
    db.commit()
    return {"message": "name set", "cluster_id": req.cluster_id, "name": req.name}
# ── POST /cleanup ────────────────────────────────────────────

@router.post("/cleanup")
def cleanup_empty_identities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """删除所有没有关联人脸的空身份聚类（0 张照片的集群）"""
    from app.services.face_cluster_service import cleanup_orphaned_identities

    result = cleanup_orphaned_identities(db, current_user.id)
    return BaseResponse(
        msg=f"已清理 {result['deleted']} 个空聚类",
        data={"deleted": result["deleted"]},
    )
