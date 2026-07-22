"""
训练与管理模块的 ORM 模型

包含三张表：
- training_task: 训练任务，记录每次训练的全生命周期信息
- dataset: 数据集，记录用户上传的 YOLO 格式数据集
- training_metric: 训练指标，存储每个 epoch 的详细指标数据（用于绘制图表）
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON,
    ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base


class Dataset(Base):
    """数据集表"""
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, comment="数据集名称")
    path = Column(String(500), nullable=False, comment="数据集存储路径")
    image_count = Column(Integer, default=0, comment="图片数量")
    class_names = Column(JSON, default=list, comment="类别名称列表（JSON 数组）")
    class_count = Column(Integer, default=0, comment="类别数量")
    file_size = Column(Integer, default=0, comment="数据集大小（字节）")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True, comment="所属用户")

    # 关联关系
    tasks = relationship("TrainingTask", back_populates="dataset_rel", lazy="dynamic")
    owner = relationship("User", backref="datasets")

    def __repr__(self):
        return f"<Dataset {self.name} ({self.image_count} imgs, {self.class_count} classes)>"


class TrainingTask(Base):
    """训练任务表"""
    __tablename__ = "training_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_name = Column(String(255), nullable=False, comment="任务名称（用户自定义）")
    model_name = Column(String(255), unique=True, nullable=False, comment="模型名称（唯一，训练完成后保存的文件名）")
    description = Column(Text, nullable=True, comment="训练描述")
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, comment="关联数据集 ID")
    status = Column(
        String(20), default="pending", index=True,
        comment="任务状态: pending/running/paused/completed/failed",
    )
    config = Column(JSON, default=dict, comment="训练超参数配置（JSON 存储所有参数）")

    # 训练进度
    current_epoch = Column(Integer, default=0, comment="当前已完成的 epoch 数")
    total_epochs = Column(Integer, default=100, comment="总 epoch 数")
    best_metric = Column(Float, nullable=True, comment="最佳 mAP50 值")

    # 文件路径
    checkpoint_path = Column(String(500), nullable=True, comment="最新 checkpoint 路径")
    model_path = Column(String(500), nullable=True, comment="最终模型文件路径")
    log_path = Column(String(500), nullable=True, comment="训练日志文件路径")

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    started_at = Column(DateTime, nullable=True, comment="开始训练时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True, comment="所属用户")

    # 关联关系
    dataset_rel = relationship("Dataset", back_populates="tasks")
    metrics = relationship(
        "TrainingMetric", back_populates="task", cascade="all, delete-orphan",
        order_by="TrainingMetric.epoch",
    )
    owner = relationship("User", backref="training_tasks")

    __table_args__ = (
        Index("idx_training_status", "status"),
        Index("idx_training_model_name", "model_name"),
    )

    def __repr__(self):
        return f"<TrainingTask {self.task_name} [{self.status}] ({self.current_epoch}/{self.total_epochs})>"


class TrainingMetric(Base):
    """训练指标表（每个 epoch 的详细指标）"""
    __tablename__ = "training_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("training_tasks.id"), nullable=False, index=True)
    epoch = Column(Integer, nullable=False, comment="当前 epoch 数")
    metrics = Column(JSON, default=dict, comment="指标字典，如 {\"train/box_loss\": 1.23, \"val/mAP50\": 0.45, ...}")
    created_at = Column(DateTime, default=datetime.now, comment="记录时间")

    # 关联关系
    task = relationship("TrainingTask", back_populates="metrics")

    __table_args__ = (
        Index("idx_metric_task_epoch", "task_id", "epoch"),
    )

    def __repr__(self):
        return f"<TrainingMetric task={self.task_id} epoch={self.epoch}>"
