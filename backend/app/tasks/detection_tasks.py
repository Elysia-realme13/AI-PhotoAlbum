"""YOLO detection tasks --- run YOLO on newly uploaded photos and store tags.

Previously these tasks were created but never executed (Phase 2-3 gap).
This module provides the actual execution logic.
"""

import json
import logging
from uuid import UUID
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.description import ImageDescription
from app.models.task import Task, TaskStatus
from app.services.detection_service import detect_objects, get_detection_summary

logger = logging.getLogger(__name__)


def process_photo_detection(
    photo_id: str,
    image_path: str,
    task_id: str = None,
) -> bool:
    """Run YOLO detection on a photo and store results in ImageDescription.tags.

    Args:
        photo_id: UUID string of the photo.
        image_path: Full file path to the image.
        task_id: Optional task UUID string; if provided, the task status is updated.

    Returns:
        True if detection succeeded, False otherwise.
    """
    db = SessionLocal()
    try:
        pid = UUID(photo_id)
    except Exception:
        logger.error(f"Invalid photo_id: {photo_id}")
        return False

    try:
        # 1. Run YOLO detection
        logger.info(f"Running YOLO detection on photo {photo_id[:8]}...")
        result = detect_objects(image_path, confidence_threshold=0.25)
        if not result.get("success"):
            logger.warning(f"YOLO detection failed for {photo_id}: {result.get('error')}")
            return False

        detections = result.get("detections", [])
        summary = get_detection_summary(detections)

        # 2. Build tags payload
        tags_payload = {
            "detections": detections,
            "summary": summary,
            "total": result.get("total", 0),
            "model": result.get("model", "best.pt"),
        }

        # 3. Upsert ImageDescription.tags
        existing = db.query(ImageDescription).filter(
            ImageDescription.photo_id == pid
        ).first()

        if existing:
            existing.tags = tags_payload
        else:
            desc = ImageDescription(
                id=uuid4(),
                photo_id=pid,
                tags=tags_payload,
            )
            db.add(desc)

        logger.info(
            f"YOLO done for {photo_id[:8]}: {len(summary)} object types, "
            f"{result['total']} total detections"
        )

        # 4. Update task status if task_id provided
        if task_id:
            _update_task_status(db, task_id, TaskStatus.completed, result=tags_payload)

        db.commit()
        return True

    except Exception as e:
        logger.error(f"YOLO detection task failed for {photo_id}: {e}")
        db.rollback()
        if task_id:
            try:
                _update_task_status(db, task_id, TaskStatus.failed, error=str(e))
                db.commit()
            except Exception:
                db.rollback()
        return False
    finally:
        db.close()


def _update_task_status(
    db: Session,
    task_id: str,
    status: TaskStatus,
    result: dict = None,
    error: str = None,
):
    """Update a task record's status, result, and error_message."""
    try:
        tid = UUID(task_id)
    except Exception:
        logger.warning(f"Invalid task_id: {task_id}")
        return

    task = db.query(Task).filter(Task.id == tid).first()
    if task:
        task.status = status
        if result:
            task.result = result
        if error:
            task.error_message = error


def run_pending_object_detection_tasks(db: Session, batch_size: int = 5) -> dict:
    """Batch processor: find and run pending object_detection tasks.

    Intended for manual trigger or a future background worker.
    """
    from app.models.task import TaskType
    from app.models.photo import Photo

    tasks = (
        db.query(Task)
        .filter(
            Task.status == TaskStatus.pending,
            Task.task_type == TaskType.object_detection,
        )
        .limit(batch_size)
        .all()
    )

    if not tasks:
        return {"processed": 0, "succeeded": 0, "failed": 0}

    stats = {"processed": 0, "succeeded": 0, "failed": 0}
    for task in tasks:
        if not task.photo_id:
            continue
        photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
        if not photo:
            continue

        stats["processed"] += 1
        success = process_photo_detection(
            photo_id=str(task.photo_id),
            image_path=photo.file_path,
            task_id=str(task.id),
        )
        if success:
            stats["succeeded"] += 1
        else:
            stats["failed"] += 1

    return stats


# Avoid circular import for uuid4
from uuid import uuid4

__all__ = [
    "process_photo_detection",
    "run_pending_object_detection_tasks",
]

