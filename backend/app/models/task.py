"""
异步任务模型（简易版）

Phase 2-3 阶段实现 Producer-Consumer 任务队列的 Producer 端。
Worker 进程将在 Phase 3 实现，当前仅创建和管理 Task 记录。

任务生命周期:
    pending → running → completed
                     → failed → (手动) pending（重试）

与现有项目的关系:
    - Photo.processed_tasks (JSON) 记录每张照片已完成的分析类型
    - Task 表记录每次分析任务的状态和结果
    - 两个字段配合使用：Task 追踪过程，processed_tasks 缓存结果
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, ForeignKey, DateTime, Text, JSON,
    Enum as SAEnum, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base


class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class TaskType(str, enum.Enum):
    face_detect = "face_detect"              # 人脸检测 + 特征提取
    face_cluster = "face_cluster"            # 全量人脸聚类
    image_description = "image_description"  # AI 画面描述
    image_embedding = "image_embedding"      # CLIP 向量嵌入
    quality_assessment = "quality_assessment" # 美观度/回忆价值评分
    thumbnail_generate = "thumbnail_generate" # 缩略图生成
    exif_extract = "exif_extract"            # EXIF 元数据提取
    dedup_check = "dedup_check"              # 重复照片检测


class Task(Base):
    """异步任务记录"""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(
        UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="关联的照片 ID（某些任务可能不关联照片）"
    )
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="任务所属用户"
    )
    task_type = Column(
        SAEnum(TaskType), nullable=False, index=True, comment="任务类型"
    )
    status = Column(
        SAEnum(TaskStatus), default=TaskStatus.pending, nullable=False, index=True,
        comment="任务状态"
    )
    progress = Column(JSON, default=dict, comment="任务进度（如 {current: 10, total: 50}）")
    result = Column(JSON, default=dict, comment="任务结果数据")
    error_message = Column(Text, nullable=True, comment="失败原因")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_tasks_status_created", "status", "created_at"),
        Index("idx_tasks_photo_type", "photo_id", "task_type"),
    )
