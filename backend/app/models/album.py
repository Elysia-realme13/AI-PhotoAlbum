"""
相册模型
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, ForeignKey, DateTime, Text, Boolean, JSON, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base


class AlbumType(str, enum.Enum):
    manual = "manual"
    smart = "smart"
    conditional = "conditional"


class Album(Base):
    __tablename__ = "albums"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False, comment="相册名称")
    description = Column(Text, comment="描述")
    cover_photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), nullable=True)
    is_system = Column(Boolean, default=False, comment="是否系统自动生成")
    album_type = Column(SAEnum(AlbumType), default=AlbumType.manual, comment="相册类型")
    conditions = Column(JSON, comment="条件相册的筛选规则")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    owner = relationship("User", back_populates="albums")
    photos = relationship("Photo", secondary="album_photos", back_populates="albums")


class AlbumPhoto(Base):
    """相册-照片关联表"""
    __tablename__ = "album_photos"

    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), primary_key=True)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), primary_key=True)
    added_at = Column(DateTime, default=datetime.now)
