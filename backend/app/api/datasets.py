"""
数据集管理 API 路由

提供数据集的 CRUD 操作、ZIP 上传、预览等功能
"""
import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.models.training import Dataset
from app.schemas.training import DatasetResponse, DatasetPreviewResponse
from app.services import training_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/datasets", tags=["数据集管理"])


@router.post("/upload", response_model=DatasetResponse, status_code=201)
def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """上传数据集压缩包（YOLO 格式：images/ 和 labels/ 目录）

    支持的格式: .zip / .tar / .tar.gz / .tgz / .tar.bz2 / .7z / .rar
    """
    SUPPORTED_EXTS = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".7z", ".rar")

    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择要上传的文件")

    fname = file.filename.lower()
    supported = any(fname.endswith(e) for e in SUPPORTED_EXTS)
    if not supported:
         raise HTTPException(
             status_code=400,
             detail=f"不支持的格式，支持: {', '.join(SUPPORTED_EXTS)}",
         )

    try:
        file_bytes = file.file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")

        dataset = training_service.upload_dataset(file_bytes, file.filename, db, user_id=current_user.id)
        return DatasetResponse.model_validate(dataset)
    except Exception as e:
        logger.error(f"上传数据集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传数据集失败: {str(e)}")


@router.get("")
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取所有数据集列表"""
    try:
        datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).order_by(Dataset.created_at.desc()).all()
        items = [DatasetResponse.model_validate(d) for d in datasets]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"获取数据集列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取数据集列表失败: {str(e)}")


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """预览数据集（类别列表和样例图片）"""
    preview = training_service.get_dataset_preview(dataset_id, db, user_id=current_user.id)
    if "error" in preview:
        raise HTTPException(status_code=404, detail=preview["error"])
    return DatasetPreviewResponse(**preview)


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """删除数据集"""
    success = training_service.delete_dataset(dataset_id, db, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return {"message": "数据集已删除"}


@router.get("/{dataset_id}/image")
def serve_dataset_image(
    dataset_id: str,
    path: str,
    db: Session = Depends(get_db),
):
    """提供数据集中的图片文件"""
    dataset = db.query(Dataset).filter(Dataset.id == uuid.UUID(dataset_id)).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    dataset_dir = Path(dataset.path).resolve()
    image_path = (dataset_dir / path).resolve()
    if not str(image_path).startswith(str(dataset_dir)):
        raise HTTPException(status_code=403, detail="非法路径")
    return FileResponse(str(image_path))


@router.get("/storage/info")
def get_storage_info(
    current_user: User = Depends(get_required_user),
):
    """获取磁盘空间信息"""
    try:
        info = training_service.get_storage_info()
        return info
    except Exception as e:
        logger.error(f"获取存储信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/storage/clean")
def clean_storage(
    current_user: User = Depends(get_required_user),
):
    """清理失败的训练任务产生的临时文件"""
    try:
        result = training_service.clean_failed_temp_files()
        return result
    except Exception as e:
        logger.error(f"清理存储失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
