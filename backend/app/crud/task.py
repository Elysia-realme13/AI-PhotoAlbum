"""
任务 CRUD 操作（简易版）

Phase 2-3: 仅创建和查询 Task 记录。
Worker 消费逻辑在 Phase 3 实现。
"""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.task import Task, TaskStatus, TaskType


def create_task(
    db: Session,
    owner_id: uuid.UUID,
    task_type: TaskType,
    photo_id: Optional[uuid.UUID] = None,
) -> Task:
    """创建任务（状态默认为 pending）"""
    task = Task(
        owner_id=owner_id,
        photo_id=photo_id,
        task_type=task_type,
        status=TaskStatus.pending,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def create_tasks_batch(
    db: Session,
    owner_id: uuid.UUID,
    photo_id: uuid.UUID,
    task_types: List[TaskType],
) -> List[Task]:
    """为同一张照片批量创建多种任务"""
    tasks = []
    for ttype in task_types:
        task = Task(
            owner_id=owner_id,
            photo_id=photo_id,
            task_type=ttype,
            status=TaskStatus.pending,
        )
        db.add(task)
        tasks.append(task)
    db.commit()
    for t in tasks:
        db.refresh(t)
    return tasks


def get_task_by_id(
    db: Session,
    task_id: uuid.UUID,
    owner_id: Optional[uuid.UUID] = None,
) -> Optional[Task]:
    """获取单个任务"""
    query = db.query(Task).filter(Task.id == task_id)
    if owner_id:
        query = query.filter(Task.owner_id == owner_id)
    return query.first()


def get_task_list(
    db: Session,
    owner_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: Optional[TaskStatus] = None,
    task_type: Optional[TaskType] = None,
    photo_id: Optional[uuid.UUID] = None,
) -> Tuple[List[Task], int]:
    """任务列表（分页 + 筛选）"""
    query = db.query(Task).filter(Task.owner_id == owner_id)

    if status:
        query = query.filter(Task.status == status)
    if task_type:
        query = query.filter(Task.task_type == task_type)
    if photo_id:
        query = query.filter(Task.photo_id == photo_id)

    total = query.count()
    offset = (page - 1) * page_size
    tasks = query.order_by(desc(Task.created_at)).offset(offset).limit(page_size).all()
    return tasks, total


def update_task_status(
    db: Session,
    task: Task,
    status: TaskStatus,
    result: Optional[dict] = None,
    error_message: Optional[str] = None,
) -> Task:
    """更新任务状态"""
    task.status = status
    if result is not None:
        task.result = result
    if error_message is not None:
        task.error_message = error_message
    db.commit()
    db.refresh(task)
    return task


def retry_task(db: Session, task: Task) -> Task:
    """重置失败任务为 pending 以重试"""
    task.status = TaskStatus.pending
    task.error_message = None
    db.commit()
    db.refresh(task)
    return task


def cancel_task(db: Session, task: Task) -> Task:
    """取消任务（仅 pending 状态可取消）"""
    if task.status == TaskStatus.pending:
        task.status = TaskStatus.failed
        task.error_message = "用户取消"
        db.commit()
        db.refresh(task)
    return task


def get_pending_tasks(
    db: Session,
    task_type: Optional[TaskType] = None,
    limit: int = 10,
) -> List[Task]:
    """
    获取待处理任务列表（供 Worker 消费，Phase 3 实现）

    按创建时间升序排列，保证先进先出。
    """
    query = db.query(Task).filter(Task.status == TaskStatus.pending)
    if task_type:
        query = query.filter(Task.task_type == task_type)
    return query.order_by(Task.created_at.asc()).limit(limit).all()


def get_task_stats(db: Session, owner_id: uuid.UUID) -> dict:
    """获取用户任务统计"""
    stats = (
        db.query(Task.status, func.count(Task.id))
        .filter(Task.owner_id == owner_id)
        .group_by(Task.status)
        .all()
    )
    result = {"total": 0, "pending": 0, "running": 0, "completed": 0, "failed": 0}
    for row in stats:
        result[row[0].value if hasattr(row[0], 'value') else row[0]] = row[1]
    result["total"] = sum(result.values())
    return result
