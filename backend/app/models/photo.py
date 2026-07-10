"""
照片模型
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, ForeignKey, DateTime, BigInteger,
    Integer, Float, Boolean, JSON, Enum as SAEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base
import enum


class FileType(str, enum.Enum):
    image = "image"
    video = "video"
    live_photo = "live_photo"


class Photo(Base):
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), index=True, comment="存储文件名")
    original_name = Column(String(255), comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_size = Column(BigInteger, comment="文件大小（字节）")
    width = Column(Integer, comment="图片宽度")
    height = Column(Integer, comment="图片高度")
    photo_time = Column(DateTime, index=True, comment="拍摄时间")
    upload_time = Column(DateTime, default=datetime.now, comment="上传时间")
    file_type = Column(SAEnum(FileType), default=FileType.image, comment="文件类型")
    md5 = Column(String(32), index=True, comment="文件MD5（去重用）")
    is_deleted = Column(Boolean, default=False, index=True, comment="软删除标记")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    processed_tasks = Column(JSON, default=dict, comment="已完成的分析任务")

    # 关联关系
    owner = relationship("User", back_populates="photos")
    metadata_info = relationship(
        "PhotoMetadata", uselist=False, back_populates="photo", cascade="all, delete-orphan"
    )
    faces = relationship("Face", back_populates="photo", cascade="all, delete-orphan")
    image_description = relationship(
        "ImageDescription", uselist=False, back_populates="photo", cascade="all, delete-orphan"
    )
    albums = relationship("Album", secondary="album_photos", back_populates="photos")
    tags = relationship("PhotoTag", secondary="photo_tag_relations", backref="photos")

    __table_args__ = (
        Index("idx_photos_owner_time", "owner_id", "photo_time"),
        Index("idx_photos_md5", "md5"),
    )


class PhotoMetadata(Base):
    """EXIF 元数据"""
    __tablename__ = "photo_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), unique=True, nullable=False)
    camera_make = Column(String(100), comment="相机制造商")
    camera_model = Column(String(100), comment="相机型号")
    lens_model = Column(String(100), comment="镜头型号")
    focal_length = Column(Float, comment="焦距")
    aperture = Column(Float, comment="光圈")
    shutter_speed = Column(String(50), comment="快门速度")
    iso = Column(Integer, comment="ISO")
    latitude = Column(Float, comment="纬度")
    longitude = Column(Float, comment="经度")
    altitude = Column(Float, comment="海拔")
    country = Column(String(100), comment="国家")
    province = Column(String(100), comment="省份")
    city = Column(String(100), comment="城市")
    district = Column(String(100), comment="区县")
    address = Column(String(500), comment="详细地址")

    photo = relationship("Photo", back_populates="metadata_info")

    __table_args__ = (
        Index("idx_metadata_location", "province", "city"),
    )
