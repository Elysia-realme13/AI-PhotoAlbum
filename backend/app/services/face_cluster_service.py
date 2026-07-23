"""
人脸增量聚类服务

功能：
  1. 对新照片中的人脸执行增量聚类（与已有 cluster_id 比较余弦相似度）
  2. 更新聚类的中心向量（每个 cluster_id 的平均 embedding）
  3. 获取聚类代表性人脸头像

依赖：现有 Face 表（face_feature Vector(512)），FaceIdentity 表
"""

import uuid
import logging
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.face import Face, FaceIdentity
from app.models.photo import Photo

logger = logging.getLogger(__name__)

# 默认聚类相似度阈值（余弦相似度）
DEFAULT_CLUSTER_THRESHOLD = 0.6


# ── 工具函数 ────────────────────────────────────────────────

def _to_uuid(val) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """
    计算两个向量的余弦相似度

    Args:
        vec_a: 向量 A（512 维 list）
        vec_b: 向量 B（512 维 list）

    Returns:
        余弦相似度 [-1, 1]
    """
    import numpy as np
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ── 聚类中心计算 ────────────────────────────────────────────

def compute_cluster_center(db: Session, cluster_id) -> Optional[List[float]]:
    """
    计算指定聚类的平均 embedding 向量（中心点）

    Args:
        db: 数据库会话
        cluster_id: FaceIdentity ID

    Returns:
        512 维平均向量，若无人脸则返回 None
    """
    cid = _to_uuid(cluster_id)
    faces = db.query(Face).filter(
        Face.face_identity_id == cid,
        Face.face_feature.isnot(None),
    ).all()

    if not faces:
        return None

    import numpy as np
    vectors = [f.face_feature for f in faces if f.face_feature]
    if not vectors:
        return None

    center = np.mean(vectors, axis=0).tolist()
    return center


def compute_all_cluster_centers(db: Session) -> dict:
    """
    计算所有现有聚类的中心向量

    Returns:
        {cluster_id_str: center_vector_list}
    """
    identities = db.query(FaceIdentity).all()
    centers = {}
    for identity in identities:
        center = compute_cluster_center(db, identity.id)
        if center is not None:
            centers[str(identity.id)] = center
    return centers


# ── 增量聚类核心函数 ────────────────────────────────────────

def update_face_clusters(
    db: Session,
    photo_id,
    threshold: float = DEFAULT_CLUSTER_THRESHOLD,
    owner_id=None,
) -> List[dict]:
    """
    对指定照片中的人脸执行增量聚类

    流程：
      1. 获取照片中所有人脸及其 embedding
      2. 获取所有现有聚类中心
      3. 对每张人脸，计算与所有中心点的余弦相似度
      4. 若最大相似度 > threshold，归入该聚类；否则创建新聚类

    Args:
        db: 数据库会话
        photo_id: 照片 ID
        threshold: 聚类相似度阈值（默认 0.6）
        owner_id: 照片所有者 ID（创建新聚类时必需）

    Returns:
        [{"face_id": int, "cluster_id": str, "similarity": float, "is_new": bool}, ...]
    """
    pid = _to_uuid(photo_id)
    owner_uuid = _to_uuid(owner_id) if owner_id else None

    # 1. 获取照片中的人脸
    faces = db.query(Face).filter(Face.photo_id == pid).all()
    if not faces:
        logger.info(f"照片 {photo_id} 中未检测到人脸，跳过聚类")
        return []

    # 2. 获取现有聚类中心
    cluster_centers = compute_all_cluster_centers(db)

    results = []
    for face in faces:
        if face.face_feature is None:
            continue

        feature = face.face_feature
        best_cluster_id = None
        best_similarity = 0.0

        # 3. 与所有聚类中心计算相似度
        for cid_str, center in cluster_centers.items():
            sim = cosine_similarity(feature, center)
            if sim > best_similarity:
                best_similarity = sim
                best_cluster_id = cid_str

        is_new = False
        if best_cluster_id and best_similarity >= threshold:
            # 归入已有聚类
            face.face_identity_id = _to_uuid(best_cluster_id)
        else:
            # 创建新聚类
            is_new = True
            identity = FaceIdentity(
                id=uuid.uuid4(),
                identity_name=None,
                owner_id=owner_uuid,
            )
            db.add(identity)
            db.flush()  # 获取 ID
            face.face_identity_id = identity.id
            best_cluster_id = str(identity.id)

        results.append({
            "face_id": face.id,
            "cluster_id": best_cluster_id,
            "similarity": round(best_similarity, 4),
            "is_new": is_new,
        })

    db.commit()

    # 5. 更新受影响聚类的中心向量（记录到 identity 描述字段）
    affected_ids = set(r["cluster_id"] for r in results)
    for cid_str in affected_ids:
        center = compute_cluster_center(db, _to_uuid(cid_str))
        if center:
            logger.debug(f"聚类 {cid_str} 中心向量已更新")

    logger.info(
        f"照片 {photo_id} 聚类完成: {len(results)} 张人脸, "
        f"{sum(1 for r in results if r['is_new'])} 个新聚类"
    )
    return results


# ── 代表性人脸查询 ──────────────────────────────────────────

def get_representative_faces(
    db: Session,
    cluster_id,
    top_k: int = 3,
) -> List[dict]:
    """
    获取指定聚类中最具代表性的几张人脸

    选择策略：
      1. 按置信度降序排列
      2. 取前 top_k 张人脸
      3. 返回包含 id, photo_id, face_rect, confidence, face_image_url

    Args:
        db: 数据库会话
        cluster_id: FaceIdentity ID
        top_k: 返回数量

    Returns:
        [{"face_id": int, "photo_id": str, "rect": [x1,y1,x2,y2],
          "confidence": float, "thumbnail_url": str}, ...]
    """
    from sqlalchemy import desc as sa_desc

    cid = _to_uuid(cluster_id)
    faces = (
        db.query(Face)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(
            Face.face_identity_id == cid,
            Face.face_feature.isnot(None),
            Photo.is_deleted == False,
        )
        .order_by(sa_desc(Face.confidence))
        .limit(top_k)
        .all()
    )

    results = []
    for face in faces:
        results.append({
            "face_id": face.id,
            "photo_id": str(face.photo_id),
            "rect": face.face_rect,
            "confidence": float(face.confidence) if face.confidence else 0,
            "thumbnail_url": f"/api/medias/{face.photo_id}/thumbnail",
        })

    return results


def get_unamed_clusters(
    db: Session,
    owner_id,
    min_face_count: int = 1,
    top_k: int = 5,
) -> List[dict]:
    """
    获取所有尚未命名（identity_name IS NULL）的聚类列表

    Args:
        db: 数据库会话
        owner_id: 用户 ID
        min_face_count: 最小人脸数过滤
        top_k: 最多返回多少个聚类

    Returns:
        [{"cluster_id": str, "face_count": int,
          "representative_faces": [...], "identity_name": None}, ...]
    """
    owner_uuid = _to_uuid(owner_id)

    # 查询所有未命名的 identity，附带人脸数（仅统计非删除照片中有效特征的人脸）
    identities = (
        db.query(
            FaceIdentity,
            func.count(Face.id).label("face_count"),
        )
        .join(Face, Face.face_identity_id == FaceIdentity.id)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(
            FaceIdentity.owner_id == owner_uuid,
            FaceIdentity.identity_name.is_(None),
            FaceIdentity.is_hidden == False,
            Photo.is_deleted == False,
            Face.face_feature.isnot(None),
        )
        .group_by(FaceIdentity.id)
        .having(func.count(Face.id) >= min_face_count)
        .order_by(func.count(Face.id).desc())
        .limit(top_k)
        .all()
    )

    results = []
    for identity, face_count in identities:
        reps = get_representative_faces(db, identity.id, top_k=3)
        results.append({
            "cluster_id": str(identity.id),
            "face_count": face_count,
            "representative_faces": reps,
            "identity_name": identity.identity_name,
        })

    return results


def get_cluster_face_photos(
    db: Session,
    cluster_id,
) -> List[str]:
    """
    获取指定聚类下所有人脸对应的 photo_id 列表（去重）

    Args:
        db: 数据库会话
        cluster_id: FaceIdentity ID

    Returns:
        photo_id 字符串列表
    """
    cid = _to_uuid(cluster_id)
    faces = (
        db.query(Face)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(
            Face.face_identity_id == cid,
            Photo.is_deleted == False,
        )
        .all()
    )
    photo_ids = list(set(str(f.photo_id) for f in faces))
    return photo_ids


__all__ = [
    "update_face_clusters",
    "compute_cluster_center",
    "compute_all_cluster_centers",
    "get_representative_faces",
    "get_unamed_clusters",
    "get_cluster_face_photos",
    "cosine_similarity",
    "DEFAULT_CLUSTER_THRESHOLD",
]


def cleanup_orphaned_identities(db: Session, owner_id) -> dict:
    """删除没有任何人脸关联的身份聚类，并先清理指向已删除照片的孤立人脸记录。

    步骤：
      1. 删除所有 photo_id 指向已软删除或不存在的照片的 Face 记录
      2. 删除 Face 记录数为 0 的 FaceIdentity

    Args:
        db: 数据库会话
        owner_id: 用户 UUID

    Returns:
        {"deleted": int, "orphan_faces": int}
    """
    from sqlalchemy import func
    import logging
    logger = logging.getLogger(__name__)

    import os

    owner_uuid = _to_uuid(owner_id)
    orphan_faces = 0
    deleted = 0

    # Step 0: 删除照片文件已丢失的人脸记录
    faces_with_missing_files = (
        db.query(Face)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(
            Photo.is_deleted == False,
            Face.face_identity_id.isnot(None),
        )
        .all()
    )
    missing_face_ids = [f.id for f in faces_with_missing_files if not os.path.exists(f.photo.file_path)]
    if missing_face_ids:
        db.query(Face).filter(Face.id.in_(missing_face_ids)).delete(synchronize_session=False)
        orphan_faces += len(missing_face_ids)
        logger.info(f"清理 {len(missing_face_ids)} 条文件缺失的人脸记录")

    # Step 1: 删除指向已软删除照片的 Face 记录
    soft_deleted_faces = (
        db.query(Face)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(
            Photo.is_deleted == True,
            Face.face_identity_id.isnot(None),
        )
        .all()
    )
    if soft_deleted_faces:
        face_ids = [f.id for f in soft_deleted_faces]
        db.query(Face).filter(Face.id.in_(face_ids)).delete(synchronize_session=False)
        orphan_faces += len(face_ids)
        logger.info(f"清理 {len(face_ids)} 条指向已删除照片的人脸记录")

    # Step 2: 删除 Face 记录中 photo_id 指向不存在的照片的记录
    # (数据库层级联应该已处理这种情况，但作为安全网保留)
    dangling_faces = (
        db.query(Face)
        .outerjoin(Photo, Photo.id == Face.photo_id)
        .filter(
            Photo.id.is_(None),  # Photo 记录不存在
            Face.face_identity_id.isnot(None),
        )
        .all()
    )
    if dangling_faces:
        face_ids = [f.id for f in dangling_faces]
        db.query(Face).filter(Face.id.in_(face_ids)).delete(synchronize_session=False)
        orphan_faces += len(face_ids)
        logger.info(f"清理 {len(face_ids)} 条指向不存在照片的人脸记录")

    # Step 3: 清理现在没有任何 Face 记录的 FaceIdentity
    results = (
        db.query(FaceIdentity)
        .outerjoin(Face, Face.face_identity_id == FaceIdentity.id)
        .filter(FaceIdentity.owner_id == owner_uuid)
        .group_by(FaceIdentity.id)
        .having(func.count(Face.id) == 0)
        .all()
    )
    for identity in results:
        db.delete(identity)
        deleted += 1

    db.commit()
    if deleted or orphan_faces:
        logger.info(f"已清理: {orphan_faces} 条孤立人脸, {deleted} 个空身份聚类")
    return {"deleted": deleted, "orphan_faces": orphan_faces}
