"""
训练任务 API 路由

提供训练任务的 CRUD 操作及训练控制接口
"""
import uuid
import logging
from typing import Optional
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.session import get_db, SessionLocal
from app.api.deps import get_required_user
from app.models.user import User
from app.models.training import TrainingTask
from sqlalchemy.orm import joinedload
from app.schemas.training import (
    TrainingTaskCreate,
    TrainingTaskResponse,
    TrainingTaskListResponse,
    TrainingTaskDetailResponse,
    TrainingMetricResponse,
)
from app.services import training_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/training", tags=["训练管理"])


def _make_db_factory():
    """创建数据库会话工厂"""
    return SessionLocal


@router.post("/tasks", response_model=TrainingTaskResponse, status_code=201)
def create_training_task(
    data: TrainingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """创建训练任务"""
    try:
        task = training_service.create_task(
            task_name=data.task_name,
            model_name=data.model_name,
            config=data.config.model_dump(),
            db=db,
            description=data.description,
            dataset_id=data.dataset_id,
        )
        return TrainingTaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建训练任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建训练任务失败: {str(e)}")


@router.post("/tasks/with-dataset", response_model=TrainingTaskResponse, status_code=201)
def create_training_task_with_dataset(
    file: UploadFile = File(...),
    task_name: str = Form(...),
    model_name: str = Form(...),
    description: Optional[str] = Form(None),
    dataset_id: Optional[str] = Form(None),
    config: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """创建训练任务并可选同时上传数据集

    与 POST /api/training/tasks 的区别：
    - 支持 multipart/form-data 格式，可同时上传数据集文件
    - 既可传入已有的 dataset_id，也可上传新数据集文件
    - file 与 dataset_id 至少提供一个
    """
    try:
        if file and file.filename:
            # 读取上传的数据集文件并一键创建任务
            file_bytes = file.file.read()
            if len(file_bytes) == 0:
                raise HTTPException(status_code=400, detail="上传的文件为空")
            task = training_service.create_task_with_dataset(
                task_name=task_name,
                model_name=model_name,
                config=json.loads(config) if config else {},
                file_bytes=file_bytes,
                filename=file.filename,
                db=db,
                description=description,
            )
        elif dataset_id:
            task = training_service.create_task(
                task_name=task_name,
                model_name=model_name,
                config=json.loads(config) if config else {},
                db=db,
                description=description,
                dataset_id=dataset_id,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="请提供数据集文件 (file) 或已有数据集 ID (dataset_id)",
            )
        return TrainingTaskResponse.model_validate(task)
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="config 参数必须是有效的 JSON 字符串")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建训练任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建训练任务失败: {str(e)}")



@router.get("/tasks", response_model=TrainingTaskListResponse)
def list_training_tasks(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取训练任务列表"""
    try:
        query = db.query(TrainingTask).options(joinedload(TrainingTask.dataset_rel)).order_by(TrainingTask.created_at.desc())
        if status:
            query = query.filter(TrainingTask.status == status)
        tasks = query.all()
 
        items = []
        for t in tasks:
            if t.config and isinstance(t.config, dict) and t.config.get("imported") is True:
                continue
            item = TrainingTaskResponse.model_validate(t)
            if t.dataset_id:
                item.dataset_name = t.dataset_rel.name if t.dataset_rel else None
            items.append(item)
 
        return TrainingTaskListResponse(total=len(items), items=items)
    except Exception as e:
        logger.error(f"获取训练任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取训练任务列表失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TrainingTaskDetailResponse)
def get_training_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取训练任务详情（含指标数据）"""
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的任务 ID")

    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    metrics = training_service.get_task_metrics(task_id, db)

    # 填充数据集名称
    task_resp = TrainingTaskResponse.model_validate(task)
    if task.dataset_id and task.dataset_rel:
        task_resp.dataset_name = task.dataset_rel.name
 
    return TrainingTaskDetailResponse(
        task=task_resp,
        metrics=[TrainingMetricResponse.model_validate(m) for m in metrics],
        logs=training_service.get_task_logs(task_id, db).get("lines", []),
    )


@router.post("/tasks/{task_id}/start")
def start_training(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """启动训练"""
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == uuid.UUID(task_id)).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的任务 ID")

    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    if task.status not in ("pending", "paused", "failed"):
        raise HTTPException(status_code=400, detail=f"当前状态不允许启动: {task.status}")

    db.commit()  # 确保状态持久化

    try:
        training_service.start_training(task_id, _make_db_factory())
        return {"message": "训练已启动", "task_id": task_id, "status": "running"}
    except Exception as e:
        logger.error(f"启动训练失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动训练失败: {str(e)}")


@router.post("/tasks/{task_id}/pause")
def pause_training_route(
    task_id: str,
    current_user: User = Depends(get_required_user),
):
    """暂停训练（完成当前 epoch 后暂停）"""
    try:
        training_service.pause_training(task_id)
        return {"message": "正在暂停训练（完成当前 epoch 后暂停）", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停训练失败: {str(e)}")


@router.post("/tasks/{task_id}/resume")
def resume_training_route(
    task_id: str,
    current_user: User = Depends(get_required_user),
):
    """恢复训练"""
    try:
        training_service.resume_training(task_id, _make_db_factory())
        return {"message": "训练已恢复", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复训练失败: {str(e)}")


@router.post("/tasks/{task_id}/stop")
def stop_training_route(
    task_id: str,
    current_user: User = Depends(get_required_user),
):
    """停止训练（不保存当前 checkpoint）"""
    try:
        training_service.stop_training(task_id)
        return {"message": "训练已停止", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止训练失败: {str(e)}")


@router.delete("/tasks/{task_id}")
def delete_training_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """删除训练任务及关联文件"""
    try:
        success = training_service.delete_training_task(task_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="训练任务不存在")
        return {"message": "训练任务已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/tasks/{task_id}/status")
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取任务状态"""
    status = training_service.get_task_status(task_id, db)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.get("/tasks/{task_id}/metrics")
def get_task_metrics(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取任务所有指标数据"""
    metrics = training_service.get_task_metrics(task_id, db)
    return {"metrics": metrics}


@router.get("/tasks/{task_id}/logs")
def get_task_logs(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取训练日志"""
    logs = training_service.get_task_logs(task_id, db)
    return logs
