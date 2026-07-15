"""
任务 API 路由（简易版）

Phase 2-3: 仅提供任务查询和重试功能。
Worker 消费逻辑在 Phase 3 实现，当前任务创建后保持 pending 状态。
"""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.models.task import TaskStatus, TaskType

from app.schemas.response import BaseResponse, PaginatedData
from app.schemas.task import TaskResponse, TaskStatsResponse

from app.crud import task as task_crud

logger = logging.getLogger("app.api.tasks")

router = APIRouter(prefix="/api/tasks", tags=["任务"])


@router.get("", response_model=BaseResponse[PaginatedData])
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="筛选状态: pending/running/completed/failed"),
    task_type: Optional[str] = Query(default=None, description="筛选类型: face_detect/image_description/..."),
    photo_id: Optional[str] = Query(default=None, description="按照片筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    任务列表

    按状态、类型、关联照片筛选。用于前端展示分析进度。
    """
    status_enum = TaskStatus(status) if status else None
    type_enum = TaskType(task_type) if task_type else None
    photo_uuid = uuid.UUID(photo_id) if photo_id else None

    tasks, total = task_crud.get_task_list(
        db=db,
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status_enum,
        task_type=type_enum,
        photo_id=photo_uuid,
    )

    items = [
        TaskResponse(
            id=str(t.id),
            photo_id=str(t.photo_id) if t.photo_id else None,
            task_type=t.task_type.value if hasattr(t.task_type, 'value') else str(t.task_type),
            status=t.status.value if hasattr(t.status, 'value') else str(t.status),
            progress=t.progress,
            result=t.result,
            error_message=t.error_message,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]

    return BaseResponse(data=PaginatedData(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    ))


@router.get("/stats", response_model=BaseResponse[TaskStatsResponse])
def get_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """任务统计（各类状态计数）"""
    stats = task_crud.get_task_stats(db, current_user.id)
    return BaseResponse(data=TaskStatsResponse(**stats))


@router.get("/{task_id}", response_model=BaseResponse[TaskResponse])
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """单个任务详情（含进度和结果）"""
    task = task_crud.get_task_by_id(db, uuid.UUID(task_id), owner_id=current_user.id)
    if not task:
        return BaseResponse(code=404, msg="任务不存在", data=None)

    return BaseResponse(data=TaskResponse(
        id=str(task.id),
        photo_id=str(task.photo_id) if task.photo_id else None,
        task_type=task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type),
        status=task.status.value if hasattr(task.status, 'value') else str(task.status),
        progress=task.progress,
        result=task.result,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    ))


@router.post("/{task_id}/retry", response_model=BaseResponse[TaskResponse])
def retry_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    重试失败任务

    将 status=failed 的任务重置为 pending。
    仅 failed 状态可重试。
    """
    task = task_crud.get_task_by_id(db, uuid.UUID(task_id), owner_id=current_user.id)
    if not task:
        return BaseResponse(code=404, msg="任务不存在", data=None)
    if task.status != TaskStatus.failed:
        return BaseResponse(code=400, msg="只能重试失败的任务", data=None)

    task = task_crud.retry_task(db, task)
    return BaseResponse(msg="任务已重置为等待状态", data=TaskResponse(
        id=str(task.id),
        photo_id=str(task.photo_id) if task.photo_id else None,
        task_type=task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type),
        status=task.status.value if hasattr(task.status, 'value') else str(task.status),
        progress=task.progress,
        result=task.result,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    ))


@router.delete("/{task_id}", response_model=BaseResponse[TaskResponse])
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    取消任务

    仅 pending 状态可取消（设为 failed 并标记"用户取消"）。
    running 状态的任务无法取消（需要 Worker 支持中断信号，Phase 3）。
    """
    task = task_crud.get_task_by_id(db, uuid.UUID(task_id), owner_id=current_user.id)
    if not task:
        return BaseResponse(code=404, msg="任务不存在", data=None)
    if task.status == TaskStatus.running:
        return BaseResponse(code=400, msg="正在执行的任务无法取消（Phase 3 将支持中断）", data=None)

    task = task_crud.cancel_task(db, task)
    return BaseResponse(msg="任务已取消", data=None)
