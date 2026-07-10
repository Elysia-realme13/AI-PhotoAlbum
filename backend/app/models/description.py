"""
AI 描述与标签模型
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, ForeignKey, Text, Float, JSON, DateTime, Integer, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database.session import Base


class ImageDescription(Base):
    """AI 生成的图片描述"""
    __tablename__ = "image_descriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), unique=True, nullable=False)
    description = Column(Text, comment="画面描述")
    narrative = Column(String(500), comment="一句话旁白")
    tags = Column(JSON, comment="标签数组")
    quality_score = Column(Float, comment="美观度评分 0-1")
    memory_score = Column(Float, comment="回忆价值评分 0-1")
    created_at = Column(DateTime, default=datetime.now)

    photo = relationship("Photo", back_populates="image_description")


class ImageVector(Base):
    """CLIP 向量嵌入"""
    __tablename__ = "image_vectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), unique=True, nullable=False)
    embedding = Column(Vector(512), comment="CLIP 向量")

    __table_args__ = (
        Index(
            "idx_image_vector_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class PhotoTag(Base):
    """标签表"""
    __tablename__ = "photo_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_name = Column(String(100), unique=True, nullable=False, comment="标签名")
    category = Column(String(50), comment="分类: scene/object/style/emotion")


class PhotoTagRelation(Base):
    """照片-标签关联表"""
    __tablename__ = "photo_tag_relations"

    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("photo_tags.id"), primary_key=True)
