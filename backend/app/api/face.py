"""
Face API - cluster naming, merging, and unamed list
GET  /api/faces/unamed   -  unnamed cluster list
POST /api/faces/name     -  bind name to cluster
POST /api/faces/merge    -  merge two clusters
"""
import uuid as _uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.models.face import Face, FaceIdentity
from app.services.face_cluster_service import get_unamed_clusters, get_representative_faces
from app.services.name_confirmation_service import confirm_name, find_clusters_by_name

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
    faces = db.query(Face).filter(Face.face_identity_id == cid).all()
    for face in faces:
        face.face_name = req.name
        if req.aliases:
            face.face_aliases = req.aliases
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
