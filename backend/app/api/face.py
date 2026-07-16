"""
Face API - cluster naming, merging, and unamed list
GET  /api/faces/unamed              -  unnamed cluster list
GET  /api/faces/identities          -  all identities (named + unnamed)
GET  /api/faces/identities/{id}/photos -  photos of an identity
POST /api/faces/name                -  bind name to cluster
POST /api/faces/merge               -  merge two clusters
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
from app.models.photo import Photo
from app.schemas.photo import PhotoResponse
from app.services.face_cluster_service import get_unamed_clusters, get_cluster_face_photos

router = APIRouter(prefix="/api/faces", tags=["faces"])


class NameBindRequest(BaseModel):
    cluster_id: str
    name: str
    aliases: Optional[List[str]] = None
    session_id: Optional[str] = None
    query: Optional[str] = None


class MergeRequest(BaseModel):
    source_cluster_id: str
    target_cluster_id: str


class ClusterInfo(BaseModel):
    cluster_id: str
    identity_name: Optional[str] = None
    face_count: int
    representative_faces: List[dict]


@router.get("/unamed", response_model=List[ClusterInfo])
def list_unamed_clusters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    clusters = get_unamed_clusters(
        db=db, owner_id=str(current_user.id), top_k=20,
    )
    return [ClusterInfo(**c) for c in clusters]


@router.post("/name")
def bind_name(
    req: NameBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    if req.session_id and req.query:
        success = confirm_name(
            db=db, session_id=req.session_id, query=req.query,
            cluster_id=req.cluster_id, name=req.name, aliases=req.aliases,
        )
        if not success:
            raise HTTPException(400, "name confirmation failed: pending session expired")
        return {"message": "name confirmed", "cluster_id": req.cluster_id, "name": req.name}

    cid = _uuid.UUID(req.cluster_id)
    identity = db.query(FaceIdentity).filter(FaceIdentity.id == cid).first()
    if not identity:
        raise HTTPException(404, "cluster not found")

    identity.identity_name = req.name
    db.commit()
    return {"message": "name set", "cluster_id": req.cluster_id, "name": req.name}


@router.post("/merge")
def merge_clusters(
    req: MergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    src = _uuid.UUID(req.source_cluster_id)
    tgt = _uuid.UUID(req.target_cluster_id)
    source_identity = db.query(FaceIdentity).filter(FaceIdentity.id == src).first()
    target_identity = db.query(FaceIdentity).filter(FaceIdentity.id == tgt).first()
    if not source_identity or not target_identity:
        raise HTTPException(404, "cluster not found")
    db.query(Face).filter(Face.face_identity_id == src).update({"face_identity_id": tgt})
    source_identity.is_hidden = True
    db.commit()
    return {
        "message": "merged",
        "source_cluster_id": req.source_cluster_id,
        "target_cluster_id": req.target_cluster_id,
    }


class IdentityResponse(BaseModel):
    identity_id: str
    identity_name: Optional[str] = None
    face_count: int
    cover_photo_id: Optional[str] = None


@router.get("/identities", response_model=List[IdentityResponse])
def list_all_identities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取所有人物聚类（含已命名和未命名）"""
    owner_id = current_user.id

    # 查询所有可见的 identity，附带人脸数
    identities = (
        db.query(
            FaceIdentity,
            func.count(Face.id).label("face_count"),
        )
        .outerjoin(Face, Face.face_identity_id == FaceIdentity.id)
        .filter(
            FaceIdentity.owner_id == owner_id,
            FaceIdentity.is_hidden == False,
        )
        .group_by(FaceIdentity.id)
        .order_by(func.count(Face.id).desc())
        .all()
    )

    results = []
    for identity, face_count in identities:
        # 获取封面照片：该聚类下第一张人脸对应的 photo_id
        first_face = (
            db.query(Face.photo_id)
            .filter(Face.face_identity_id == identity.id)
            .first()
        )
        cover_photo_id = str(first_face.photo_id) if first_face else None

        results.append(IdentityResponse(
            identity_id=str(identity.id),
            identity_name=identity.identity_name,
            face_count=face_count,
            cover_photo_id=cover_photo_id,
        ))

    return results


@router.get("/identities/{identity_id}/photos", response_model=List[PhotoResponse])
def get_identity_photos(
    identity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取某人物聚类下的所有照片"""
    iid = _uuid.UUID(identity_id)
    identity = db.query(FaceIdentity).filter(FaceIdentity.id == iid).first()
    if not identity:
        raise HTTPException(404, "人物不存在")
    if str(identity.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权访问")

    # 获取该聚类下所有 photo_id
    photo_ids = get_cluster_face_photos(db, identity_id)
    if not photo_ids:
        return []

    # 查询照片详情
    photos = (
        db.query(Photo)
        .filter(Photo.id.in_([_uuid.UUID(pid) for pid in photo_ids]))
        .all()
    )
    return [PhotoResponse.model_validate(p) for p in photos]
