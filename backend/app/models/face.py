"""
人脸模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, DECIMAL, JSON, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database.session import Base


class FaceIdentity(Base):
    """人脸身份聚类"""
    __tablename__ = "face_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_name = Column(String(500), index=True, comment="人物名称（用户命名）")
    description = Column(String(500), nullable=True, comment="描述")
    default_face_id = Column(
        Integer, ForeignKey("faces.id", ondelete="SET NULL"), nullable=True
    )
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at = Column(DateTime, default=datetime.now)
    is_hidden = Column(Boolean, default=False, comment="是否隐藏")

    # 关联关系
    owner = relationship("User", back_populates="face_identities")
    faces = relationship("Face", back_populates="identity", foreign_keys="Face.face_identity_id")


class Face(Base):
    """人脸检测结果"""
    __tablename__ = "faces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False)
    face_identity_id = Column(
        UUID(as_uuid=True), ForeignKey("face_identities.id", ondelete="SET NULL"), nullable=True
    )
    face_feature = Column(Vector(512), comment="人脸特征向量")
    face_rect = Column(JSON, comment="检测框 [x1, y1, x2, y2]")
    confidence = Column(DECIMAL(5, 4), comment="检测置信度")
    created_at = Column(DateTime, default=datetime.now)

    # 关联关系
    photo = relationship("Photo", back_populates="faces")
    identity = relationship("FaceIdentity", back_populates="faces", foreign_keys=[face_identity_id])

    __table_args__ = (
        Index("idx_face_photo_id", "photo_id"),
        Index("idx_face_identity_id", "face_identity_id"),
    )
