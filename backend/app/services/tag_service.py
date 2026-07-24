"""
标签服务 — YOLO 目标检测 → 自动生成照片标签

流程:
  1. 对照片运行 YOLO 检测
  2. 提取 top-N 标签
  3. 写入 ImageDescription.tags
  4. 更新 Task 状态
"""

import logging
from typing import List, Optional
from typing import Any
from sqlalchemy.orm import Session

from app.models.photo import Photo
from app.models.task import Task, TaskType, TaskStatus
from app.models.description import ImageDescription
from app.services.detection_service import detect_objects, get_detection_summary

logger = logging.getLogger("app.services.tag")


def run_object_detection(photo: Photo, top_k: int = 10) -> List[dict]:
    """对一张照片运行 YOLO 目标检测，返回 [{label, count, max_confidence}]"""
    try:
        result = detect_objects(photo.file_path, confidence_threshold=0.3)
        if not result.get("success"):
            logger.warning(f"检测失败: {result.get('error', '未知错误')}")
            return []
        summary = get_detection_summary(result["detections"])
        logger.info(f"检测完成: {photo.filename} → {[s['label'] for s in summary[:top_k]]}")
        return summary[:top_k]
    except Exception as e:
        logger.warning(f"YOLO 检测失败 {photo.filename}: {e}")
        return []


def generate_tags_for_photo(db: Session, photo: Photo) -> Optional[ImageDescription]:
    """对一张照片运行检测，将标签写入 ImageDescription.tags（dict 格式）"""
    items = run_object_detection(photo)
    tags_payload = {"detections": [], "summary": items, "total": len(items), "model": "best.pt"}

    desc = db.query(ImageDescription).filter(
        ImageDescription.photo_id == photo.id
    ).first()

    if desc:
        old_summary = desc.tags.get("summary", []) if isinstance(desc.tags, dict) else []
        existing_labels = {s["label"] for s in old_summary if isinstance(s, dict) and "label" in s}
        new_labels = {s["label"] for s in items if isinstance(s, dict) and "label" in s}
        # 新检测优先（含真实置信度），旧标签中未被重新检测的保留
        merged = list(items)
        for old in old_summary:
            if isinstance(old, dict) and old.get("label") and old["label"] not in new_labels:
                merged.append(old)
        tags_payload = {"detections": [], "summary": merged, "total": len(merged), "model": "best.pt"}
        desc.tags = tags_payload
    else:
        import uuid
        desc = ImageDescription(id=uuid.uuid4(), photo_id=photo.id, tags=tags_payload)
        db.add(desc)

    db.commit()
    db.refresh(desc)

    # 标记照片已完成此任务
    from app.crud.photo import update_processed_tasks
    update_processed_tasks(db, photo, "object_detection", {"labels": [s["label"] for s in items]})

    return desc


def process_pending_detection_tasks(db: Session, limit: int = 10) -> dict:
    """
    处理待处理的 object_detection 任务

    从任务队列取出 pending 任务 → 运行 YOLO → 写标签 → 更新任务状态
    """
    from app.crud.task import update_task_status

    tasks = (
        db.query(Task)
        .filter(
            Task.task_type == TaskType.object_detection,
            Task.status == TaskStatus.pending,
        )
        .order_by(Task.created_at.asc())
        .limit(limit)
        .all()
    )

    completed, failed = 0, 0
    for task in tasks:
        try:
            # 标记 running
            update_task_status(db, task, TaskStatus.running)

            photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
            if not photo:
                update_task_status(db, task, TaskStatus.failed, error_message="照片不存在")
                failed += 1
                continue

            desc = generate_tags_for_photo(db, photo)
            labels = [s["label"] for s in (desc.tags.get("summary", []) if isinstance(desc.tags, dict) else [])] if desc else []

            update_task_status(
                db, task, TaskStatus.completed,
                result={"labels": labels, "count": len(labels)},
            )
            completed += 1

        except Exception as e:
            logger.error(f"任务 {task.id} 失败: {e}")
            update_task_status(db, task, TaskStatus.failed, error_message=str(e))
            failed += 1

    return {"completed": completed, "failed": failed, "total": len(tasks)}


def batch_generate_tags(db: Session, owner_id, limit: int = 50) -> dict:
    """
    为所有缺少标签的照片批量生成标签（无需 task）
    """
    photos = (
        db.query(Photo)
        .outerjoin(ImageDescription, ImageDescription.photo_id == Photo.id)
        .filter(
            Photo.owner_id == owner_id,
            Photo.is_deleted == False,
        )
        .limit(limit)
        .all()
    )

    tagged = 0
    for photo in photos:
        try:
            desc = generate_tags_for_photo(db, photo)
            if desc:
                tagged += 1
        except Exception as e:
            logger.warning(f"跳过 {photo.filename}: {e}")

    return {"tagged": tagged, "total": len(photos)}
