"""
训练与管理模块的 Pydantic Schemas

定义训练任务、数据集、模型管理相关的请求/响应模型
"""
import uuid
from typing import Optional, Any, List, Dict
from datetime import datetime
from pydantic import BaseModel, field_validator


# ── 辅助函数 ─────────────────────────────────────────────────────
def coerce_uuid(v: Any) -> Optional[str]:
    """将 UUID 对象转为字符串"""
    if v is None:
        return None
    return str(v) if isinstance(v, uuid.UUID) else v


# ── 数据表 Schema ─────────────────────────────────────────────────

class DatasetResponse(BaseModel):
    """数据集响应"""
    id: str
    name: str
    path: str
    image_count: int = 0
    class_names: List[str] = []
    class_count: int = 0
    file_size: int = 0
    created_at: Optional[datetime] = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v):
        return coerce_uuid(v)

    model_config = {"from_attributes": True}


class DatasetPreviewResponse(BaseModel):
    """数据集预览响应（包含样例图片路径）"""
    id: str
    name: str
    class_names: List[str] = []
    sample_images: List[str] = []
    image_count: int = 0
    sample_image_urls: List[str] = []

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v):
        return coerce_uuid(v)


# ── 训练任务 Schema ──────────────────────────────────────────────

class TrainingConfig(BaseModel):
    """训练超参数配置"""
    pretrained_model: str = "yolo26n.pt"
    imgsz: int = 640
    epochs: int = 100
    batch: int = 16
    lr0: float = 0.01
    optimizer: str = "AdamW"
    momentum: float = 0.937
    weight_decay: float = 0.0005
    warmup_epochs: float = 3.0
    multi_scale: bool = False
    mixup: float = 0.0
    mosaic: float = 1.0
    copy_paste: float = 0.0
    device: str = ""
    workers: int = 8
    seed: int = 0
    save_period: int = -1
    patience: int = 50
    val_split: float = 0.2
    use_dataset_split: bool = False


class TrainingTaskCreate(BaseModel):
    """创建训练任务的请求"""
    task_name: str
    model_name: str
    description: Optional[str] = None
    dataset_id: str
    config: TrainingConfig = TrainingConfig()


class TrainingTaskResponse(BaseModel):
    """训练任务响应"""
    id: str
    task_name: str
    model_name: str
    description: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    status: str = "pending"
    config: Optional[Dict[str, Any]] = {}
    current_epoch: int = 0
    total_epochs: int = 100
    best_metric: Optional[float] = None
    checkpoint_path: Optional[str] = None
    model_path: Optional[str] = None
    log_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @field_validator("id", "dataset_id", mode="before")
    @classmethod
    def coerce_ids(cls, v):
        return coerce_uuid(v)

    model_config = {"from_attributes": True}


class TrainingTaskListResponse(BaseModel):
    """训练任务列表响应"""
    total: int
    items: List[TrainingTaskResponse]


class TrainingMetricResponse(BaseModel):
    """训练指标响应（单个 epoch）"""
    id: str
    task_id: str
    epoch: int
    metrics: Dict[str, Any] = {}
    created_at: Optional[datetime] = None

    @field_validator("id", "task_id", mode="before")
    @classmethod
    def coerce_ids(cls, v):
        return coerce_uuid(v)

    model_config = {"from_attributes": True}


class TrainingTaskDetailResponse(BaseModel):
    """训练任务详情（含指标数据）"""
    task: TrainingTaskResponse
    metrics: List[TrainingMetricResponse] = []


# ── 模型管理 Schema ──────────────────────────────────────────────

class ModelResponse(BaseModel):
    """模型信息响应（从训练任务派生）"""
    id: str
    model_name: str
    task_name: str
    status: str
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    best_metric: Optional[float] = None
    mAP50: Optional[float] = None
    mAP50_95: Optional[float] = None
    recall: Optional[float] = None
    precision: Optional[float] = None
    class_count: Optional[int] = None
    dataset_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_default: bool = False
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v):
        return coerce_uuid(v)

    model_config = {"from_attributes": True}


class ModelListResponse(BaseModel):
    """模型列表响应"""
    total: int
    items: List[ModelResponse]


class ModelDetailResponse(BaseModel):
    """模型详情（含完整训练指标数据）"""
    model: ModelResponse
    task_detail: Optional[TrainingTaskResponse] = None
    metrics: List[TrainingMetricResponse] = []


class ModelDeleteResponse(BaseModel):
    """删除模型响应"""
    message: str


# ── 存储信息 Schema ──────────────────────────────────────────────

class StorageInfoResponse(BaseModel):
    """磁盘空间信息"""
    models_size: int = 0
    datasets_size: int = 0
    logs_size: int = 0
    total_size: int = 0
    models_size_display: str = "0 B"
    datasets_size_display: str = "0 B"
    logs_size_display: str = "0 B"
    total_size_display: str = "0 B"
