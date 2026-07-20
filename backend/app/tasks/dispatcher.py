"""
任务分发器 — 任务队列的消费端

上传时 photo_service 通过 create_tasks_batch 创建 pending 任务，本模块负责消费：
    pending → running → completed / failed

设计:
    - TASK_HANDLERS 处理器注册表：包含已具备能力的任务类型 + 占位任务类型。
    - run_pending_tasks 只领取注册表中存在的类型。
    - 尚未接入模型的任务类型（face_detect / image_description / quality_assessment）
      注册占位 handler：被领取后直接消费为 completed，result 标注 skipped/未接入，
      避免其永久停留 pending（前端表现为“等待中”不动）。真实实现就绪后，直接替换
      TASK_HANDLERS 中对应项即可，无需改动调度器与上游任务创建逻辑。

扩展点（多 worker）:
    当前按单进程/单调度器设计，逐条领取无竞争。若未来多 worker 并发消费，
    应改为 SELECT ... FOR UPDATE SKIP LOCKED 原子领取，避免重复处理。
"""

import logging
from typing import Callable, Dict, List

from sqlalchemy.orm import Session

from app.crud.task import update_task_status
from app.models.photo import Photo, PhotoMetadata
from app.models.task import Task, TaskStatus, TaskType

logger = logging.getLogger("app.tasks.dispatcher")

# PhotoMetadata 的可写列（用于过滤 extract_exif 返回的多余字段，如 width/height/photo_time）
_META_FIELDS = {
    c.name for c in PhotoMetadata.__table__.columns
    if c.name not in ("id", "photo_id")
}


def _get_photo(db: Session, task: Task) -> Photo:
    """取出任务关联照片，缺失则抛异常（由调用方置 failed）"""
    if not task.photo_id:
        raise ValueError("任务缺少 photo_id")
    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        raise ValueError("照片不存在")
    return photo


def _handle_object_detection(db: Session, task: Task) -> dict:
    """YOLO 目标检测 → 自动标签"""
    from app.services.tag_service import generate_tags_for_photo

    photo = _get_photo(db, task)
    desc = generate_tags_for_photo(db, photo)
    labels = desc.tags if desc else []
    return {"labels": labels, "count": len(labels)}


def _handle_image_embedding(db: Session, task: Task) -> dict:
    """CLIP 向量嵌入"""
    from app.services.photo_vector_service import generate_photo_vector, has_vector

    photo = _get_photo(db, task)
    if has_vector(db, photo.id):
        return {"vector": True, "skipped": True}
    vector = generate_photo_vector(db, str(photo.id), photo.file_path)
    return {"vector": vector is not None}


def _handle_exif_extract(db: Session, task: Task) -> dict:
    """EXIF 元数据提取（上传时已内联提取，handler 幂等补齐）"""
    from app.crud.photo import create_photo_metadata, update_processed_tasks
    from app.services.exif_service import extract_exif

    photo = _get_photo(db, task)

    # 已有元数据则视为完成，避免重复解析
    if photo.metadata_info is not None:
        update_processed_tasks(db, photo, "exif_extract", {"applied": False})
        return {"applied": False}

    exif = extract_exif(photo.file_path)
    # 仅保留 PhotoMetadata 列且非空的字段
    meta = {k: v for k, v in exif.items() if k in _META_FIELDS and v is not None}
    if meta:
        create_photo_metadata(db, photo_id=photo.id, **meta)
    update_processed_tasks(db, photo, "exif_extract", {"applied": bool(meta)})
    return {"applied": bool(meta)}


def _handle_geocode(db: Session, task: Task) -> dict:
    """反向地理编码：GPS 经纬度 → 省/市/区，回填 PhotoMetadata"""
    from app.crud.photo import create_photo_metadata, update_processed_tasks
    from app.services.geocode_service import reverse_geocode

    photo = _get_photo(db, task)
    meta = photo.metadata_info
    if meta is None or meta.latitude is None or meta.longitude is None:
        update_processed_tasks(db, photo, "geocode", {"applied": False, "reason": "no_gps"})
        return {"applied": False, "reason": "no_gps"}

    # 已解析出城市则跳过，避免重复请求
    if meta.city:
        return {"applied": False, "reason": "already"}

    geo = reverse_geocode(meta.latitude, meta.longitude)
    if not geo:
        update_processed_tasks(db, photo, "geocode", {"applied": False, "reason": "no_result"})
        return {"applied": False, "reason": "no_result"}

    create_photo_metadata(db, photo_id=photo.id, **geo)
    update_processed_tasks(db, photo, "geocode", {"applied": True, "city": geo.get("city")})
    return {"applied": True, "city": geo.get("city")}


# 处理器注册表：仅注册当前已具备能力的任务类型
def _handle_face_detect(db: Session, task: Task) -> dict:
    """人脸检测 + 特征提取 + 增量聚类"""
    from app.services.face_detect_service import detect_faces
    from app.models.face import Face
    from app.services.face_cluster_service import update_face_clusters
    from app.crud.photo import update_processed_tasks

    photo = _get_photo(db, task)
    if not photo:
        return {"error": "photo not found"}

    faces = detect_faces(photo.file_path)
    for f in faces:
        face_obj = Face(
            photo_id=photo.id,
            face_feature=f["embedding"],
            face_rect=f["bbox"],
            confidence=f["confidence"],
        )
        db.add(face_obj)
    db.flush()

    # Incremental clustering
    update_face_clusters(db, photo.id, owner_id=task.owner_id)

    update_processed_tasks(db, photo, "face_detect", {"faces": len(faces)})
    return {"faces": len(faces)}

def _handle_image_description(db: Session, task: Task) -> dict:
    """AI 画面描述 — 使用 ChatOpenAI 生成照片的文字描述"""
    from app.crud.photo import update_processed_tasks
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    import base64

    photo = _get_photo(db, task)
    if not photo:
        return {"error": "photo not found"}

    try:
        with open(photo.file_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        llm = ChatOpenAI(model="gpt-4o", temperature=0.3, max_tokens=300)
        msg = HumanMessage(content=[
            {"type": "text", "text": "用中文简洁描述这张照片的画面内容。先一句话概括，然后用几个关键词描述。格式：\\n```\\n描述：...\\n关键词：A, B, C\\n```"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
        ])
        resp = llm.invoke([msg])
        text = resp.content if hasattr(resp, "content") else str(resp)

        desc_text = ""
        keywords = ""
        for line in text.split("\\n"):
            if line.startswith("描述") or line.startswith("描述："):
                desc_text = line.split("：", 1)[1] if "：" in line else line
            elif line.startswith("关键词") or line.startswith("关键词："):
                keywords = line.split("：", 1)[1] if "：" in line else line

        existing = _get_or_create_description(db, photo.id)
        existing.description = desc_text or text
        existing.narrative = keywords or text[:100]
        db.commit()

        update_processed_tasks(db, photo, "image_description", {"applied": True})
        return {"applied": True, "description": desc_text or text}
    except Exception as e:
        logger.error(f"Image description failed: {e}")
        update_processed_tasks(db, photo, "image_description", {"error": str(e)})
        return {"applied": False, "error": str(e)}


def _handle_quality_assessment(db: Session, task: Task) -> dict:
    """美观度/回忆价值评分 — 基于图像属性的启发式评分"""
    from app.crud.photo import update_processed_tasks
    from PIL import Image
    import math

    photo = _get_photo(db, task)
    if not photo:
        return {"error": "photo not found"}

    quality = 0.5  # 默认中等
    memory = 0.5

    try:
        img = Image.open(photo.file_path)
        w, h = img.size
        mega = (w * h) / 1_000_000

        # 质量评分：分辨率越高越好（但非线性）
        if mega >= 12:
            quality = 0.85  # 超高清
        elif mega >= 5:
            quality = 0.7   # 高清
        elif mega >= 2:
            quality = 0.55  # 普通
        else:
            quality = 0.4   # 小图

        # 回忆价值：宽幅/特殊比例更有叙事感
        aspect = max(w, h) / min(w, h) if min(w, h) > 0 else 1
        if aspect > 2.5 or aspect < 1.1:
            memory = 0.6  # 全景/特写
        else:
            memory = 0.5

        # 有 EXIF 则加分（可能是认真拍摄的）
        exif_raw = img._getexif() if hasattr(img, "_getexif") else None
        if exif_raw and len(exif_raw) > 5:
            quality = min(1.0, quality + 0.1)
            memory = min(1.0, memory + 0.05)

        img.close()

    except Exception as e:
        logger.warning(f"Quality assessment failed for {photo.filename}: {e}")

    quality = round(min(1.0, max(0.0, quality)), 2)
    memory = round(min(1.0, max(0.0, memory)), 2)

    existing = _get_or_create_description(db, photo.id)
    existing.quality_score = quality
    existing.memory_score = memory
    db.commit()

    update_processed_tasks(db, photo, "quality_assessment",
                           {"quality_score": quality, "memory_score": memory})
    return {"quality_score": quality, "memory_score": memory}


TASK_HANDLERS: Dict[TaskType, Callable[[Session, Task], dict]] = {
    TaskType.object_detection: _handle_object_detection,
    TaskType.image_embedding: _handle_image_embedding,
    TaskType.exif_extract: _handle_exif_extract,
    TaskType.geocode: _handle_geocode,
    TaskType.face_detect: _handle_face_detect,
    TaskType.image_description: _handle_image_description,
    TaskType.quality_assessment: _handle_quality_assessment,
}


def _get_or_create_description(db, photo_id):
    """获取或创建 ImageDescription 记录。"""
    from app.models.description import ImageDescription
    import uuid

    existing = db.query(ImageDescription).filter(
        ImageDescription.photo_id == photo_id
    ).first()
    if existing:
        return existing

    desc = ImageDescription(id=uuid.uuid4(), photo_id=photo_id)
    db.add(desc)
    db.flush()
    return desc


def run_pending_tasks(db: Session, limit: int = 10) -> dict:
    """
    领取并执行 pending 任务

    只处理 TASK_HANDLERS 中已注册的任务类型，按创建时间升序（FIFO）。
    单个任务异常仅置该任务 failed，不影响其余任务。

    Returns:
        {"completed": int, "failed": int, "total": int}
    """
    handled_types: List[TaskType] = list(TASK_HANDLERS.keys())
    tasks = (
        db.query(Task)
        .filter(
            Task.status == TaskStatus.pending,
            Task.task_type.in_(handled_types),
        )
        .order_by(Task.created_at.asc())
        .limit(limit)
        .all()
    )

    completed, failed = 0, 0
    for task in tasks:
        handler = TASK_HANDLERS[task.task_type]
        try:
            update_task_status(db, task, TaskStatus.running)
            result = handler(db, task)
            update_task_status(db, task, TaskStatus.completed, result=result)
            completed += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"任务 {task.id}({task.task_type}) 失败: {e}")
            db.rollback()
            update_task_status(db, task, TaskStatus.failed, error_message=str(e))
            failed += 1

    return {"completed": completed, "failed": failed, "total": len(tasks)}


__all__ = ["TASK_HANDLERS", "PLACEHOLDER_TASK_TYPES", "run_pending_tasks"]
