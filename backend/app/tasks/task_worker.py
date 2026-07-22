"""
任务 Worker — 后台消费 pending 任务并执行 AI 分析

启动方式: main.py 的 lifespan 中调用 start_worker()
"""
import logging
import uuid
import time
import threading
from typing import Optional

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.task import Task, TaskType, TaskStatus
from app.models.photo import Photo
from app.crud.task import get_pending_tasks, update_task_status
from app.crud.photo import update_processed_tasks

logger = logging.getLogger("app.tasks.worker")

_worker_thread: Optional[threading.Thread] = None
_stop_flag = threading.Event()


# ═══════════════════════════════════════════════════
# 各任务类型的处理器
# ═══════════════════════════════════════════════════


def _handle_object_detection(db: Session, task: Task) -> dict:
    """YOLO 目标检测 → 自动标签"""
    from app.services.tag_service import generate_tags_for_photo
    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}
    desc = generate_tags_for_photo(db, photo)
    labels = desc.tags if desc else []
    return {"labels": labels, "count": len(labels)}


def _handle_image_embedding(db: Session, task: Task) -> dict:
    """CLIP 向量嵌入"""
    from app.services.photo_vector_service import generate_photo_vector
    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}
    # 设置进度提示
    task.progress = {"message": "正在加载 CLIP 模型并生成特征向量"}
    db.commit()
    result = generate_photo_vector(db, str(photo.id), photo.file_path)
    return {"success": result is not None}


def _handle_image_description(db: Session, task: Task) -> dict:
    """AI 画面描述（使用多模态 LLM 看图生成）"""
    import base64
    from app.services.agent.llm_agent import get_vision_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}

    # 读取照片文件并编码为 base64
    import os
    if not os.path.exists(photo.file_path):
        return {"error": f"文件不存在: {photo.file_path}"}

    with open(photo.file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(photo.file_path)[1].lower()
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext.lstrip("."), "jpeg")

    # 用已检测的标签作为额外上下文
    tags_hint = ""
    from app.models.description import ImageDescription
    desc_row = db.query(ImageDescription).filter(ImageDescription.photo_id == task.photo_id).first()
    if desc_row and desc_row.tags:
        sum_labels = [s.get("label", "") for s in desc_row.tags.get("summary", []) if isinstance(s, dict)]
        tags_hint = f" 已检测到物体: {', '.join(sum_labels)}。" if sum_labels else ""

    try:
        llm = get_vision_llm()
        # 检查 API Key 是否为空，为空则直接跳过 LLM 调用走降级
        from app.config.settings import settings as _settings
        _key = _settings.VISION_API_KEY or _settings.OPENAI_API_KEY
        if not _key:
            raise ValueError('LLM API Key 未配置，降级到 YOLO 标签描述')
        response = llm.invoke([
            SystemMessage(content="你是专业摄影师，用中文简短描述画面（20-50字），包括场景、主体、光线和氛围。"),
            HumanMessage(content=[
                {"type": "text", "text": f"请描述这张照片的画面内容。{tags_hint}"},
                {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{image_data}"}},
            ]),
        ])
        description = response.content.strip() if hasattr(response, 'content') else str(response)

        # 存储到 ImageDescription
        if desc_row:
            desc_row.description = description
        else:
            desc_row = ImageDescription(
                id=uuid.uuid4(), photo_id=task.photo_id,
                description=description,
            )
            db.add(desc_row)
        db.commit()

        return {"description": description}
    except Exception as e:
        logger.exception(f'LLM 描述失败: {e}，降级到 YOLO 标签描述')

    # 降级路径：从 YOLO 标签生成描述
    try:
        from app.models.description import ImageDescription as _DescModel
        from collections import Counter
        existing = db.query(_DescModel).filter(_DescModel.photo_id == task.photo_id).first()
        tags = existing.tags if existing else None
        if tags and isinstance(tags, dict):
            summary = tags.get("summary", [])
            labels = [s.get('label', '') for s in summary if isinstance(s, dict) and 'label' in s]
        elif tags and isinstance(tags, list):
            labels = [t for t in tags if isinstance(t, str)]
        else:
            labels = []
        items = list(Counter(labels).items()) if labels else []
        if items:
            parts = []
            for label, cnt in items:
                parts.append(f"{label}\u00d7{cnt}" if cnt > 1 else label)
            desc_text = "照片中包含：" + "、".join(parts)
            narrative_text = "照片中的主要元素：" + "、".join(label for label, _ in items[:3])
        else:
            desc_text = None
            narrative_text = None
        if desc_row:
            desc_row.description = desc_text
            desc_row.narrative = narrative_text
        else:
            desc_row = _DescModel(
                id=uuid.uuid4(), photo_id=task.photo_id,
                description=desc_text, narrative=narrative_text,
            )
            db.add(desc_row)
        db.commit()
        return {
            "applied": True,
            "source": "yolo_fallback",
            "description": desc_text,
        }
    except Exception as e2:
        logger.error(f'YOLO 标签描述也失败: {e2}')
        return {'error': f'降级描述也失败: {e2}'}



def _handle_quality_assessment(db: Session, task: Task) -> dict:
    """照片质量评分（视觉LLM看图评估）"""
    import base64, os, json, re
    from app.services.agent.llm_agent import get_vision_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}

    if not os.path.exists(photo.file_path):
        return {"error": f"文件不存在: {photo.file_path}"}

    with open(photo.file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(photo.file_path)[1].lower()
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext.lstrip("."), "jpeg")

    from app.models.description import ImageDescription
    desc_row = db.query(ImageDescription).filter(ImageDescription.photo_id == task.photo_id).first()
    tags_hint = ""
    if desc_row and desc_row.tags:
        tags_hint = f" 已检测物体: {', '.join([t for t in desc_row.tags if isinstance(t, str)])}。"

    try:
        llm = get_vision_llm()
        # 检查 API Key 是否为空
        from app.config.settings import settings as _settings
        _key = _settings.VISION_API_KEY or _settings.OPENAI_API_KEY
        if not _key:
            raise ValueError('LLM API Key 未配置，降级到启发式评分')
        response = llm.invoke([
            SystemMessage(content="你是专业摄影评审。严格按以下标准给照片评分(0-1)：\n"
                "质量分: 清晰度/构图/光线/色彩。模糊/过曝/噪点多→低分，清晰/构图好/光线佳→高分\n"
                "记忆分: 情感价值/独特性。普通随手拍→低分，重要时刻/人物/场景→高分\n"
                "只返回JSON: {\"quality\":0.X,\"memory\":0.X,\"reason\":\"短评\"}"),
            HumanMessage(content=[
                {"type": "text", "text": f"请给这张照片打分。{tags_hint}"},
                {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{image_data}"}},
            ]),
        ])
        text = response.content.strip() if hasattr(response, 'content') else str(response)
        # 解析 JSON
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            data = json.loads(json_match.group())
            quality = max(0, min(1, float(data.get("quality", 0.5))))
            memory = max(0, min(1, float(data.get("memory", 0.5))))
            reason = data.get("reason", "")
        else:
            quality, memory, reason = 0.5, 0.5, "解析失败"
    except Exception as e:
        logger.exception(f'LLM 评分失败: {e}，降级到启发式评分')
        # 降级路径：PIL 启发式评分
        quality = 0.5
        memory = 0.5
        try:
            from PIL import Image as _PILImage
            import math
            img = _PILImage.open(photo.file_path)
            w, h = img.size
            mega = (w * h) / 1_000_000
            if mega >= 12:
                quality = 0.85
            elif mega >= 5:
                quality = 0.7
            elif mega >= 2:
                quality = 0.55
            else:
                quality = 0.4
            aspect = max(w, h) / min(w, h) if min(w, h) > 0 else 1
            if aspect > 2.5 or aspect < 1.1:
                memory = 0.6
            else:
                memory = 0.5
            exif_raw = img._getexif() if hasattr(img, '_getexif') else None
            if exif_raw and len(exif_raw) > 5:
                quality = min(1.0, quality + 0.1)
                memory = min(1.0, memory + 0.05)
            img.close()
        except Exception as e2:
            logger.warning(f'启发式评分也失败: {e2}')
        quality = round(min(1.0, max(0.0, quality)), 2)
        memory = round(min(1.0, max(0.0, memory)), 2)
        reason = "heuristic"


    quality = round(quality, 2)
    memory = round(memory, 2)

    if desc_row:
        desc_row.quality_score = quality
        desc_row.memory_score = memory
    else:
        desc_row = ImageDescription(
            id=uuid.uuid4(), photo_id=task.photo_id,
            quality_score=quality, memory_score=memory,
        )
        db.add(desc_row)
    db.commit()

    return {"quality_score": quality, "memory_score": memory, "reason": reason}


def _handle_exif_extract(db: Session, task: Task) -> dict:
    """EXIF 元数据提取（上传时已提取，这里只做标记）"""
    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}

    from app.models.photo import PhotoMetadata
    meta = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == task.photo_id).first()
    return {"has_metadata": meta is not None}


def _handle_face_detect(db: Session, task: Task) -> dict:
    """人脸检测（依赖 insightface，模型未安装时跳过）"""
    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}

    try:
        from app.services.face_detection import detect_faces
        faces = detect_faces(photo.file_path)
        if faces is None:
            return {"faces": 0, "note": "insightface 模型未安装，跳过人脸检测"}

        from app.models.face import Face, FaceIdentity
        for f in faces:
            face = Face(
                photo_id=task.photo_id,
                face_feature=f.get("embedding"),
                face_rect=f.get("bbox"),
                confidence=f.get("confidence", 0),
            )
            db.add(face)
        db.commit()

        # 触发增量聚类
        from app.services.face_cluster_service import update_face_clusters
        update_face_clusters(db, str(task.photo_id), owner_id=str(photo.owner_id))

        return {"faces": len(faces)}
    except ImportError:
        return {"faces": 0, "note": "insightface 未安装"}


def _handle_face_cluster(db: Session, task: Task) -> dict:
    """全量人脸聚类（处理所有未分配身份的人脸）"""
    try:
        from app.services.face_cluster_service import compute_all_cluster_centers
        clusters = compute_all_cluster_centers(db)
        return {"clusters_updated": len(clusters)}
    except Exception as e:
        return {"error": f"人脸聚类失败: {e}"}


def _handle_thumbnail_generate(db: Session, task: Task) -> dict:
    """生成缩略图"""
    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}

    try:
        from PIL import Image
        from app.services.thumbnail import generate_thumbnail_bytes
        from app.config.settings import settings
        from pathlib import Path

        with open(photo.file_path, "rb") as f:
            image_bytes = f.read()

        thumb_bytes = generate_thumbnail_bytes(image_bytes)
        thumb_dir = Path(settings.THUMBNAIL_DIR)
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{photo.filename}_thumb.jpg"

        with open(thumb_path, "wb") as f:
            f.write(thumb_bytes)

        return {"thumbnail_path": str(thumb_path)}
    except Exception as e:
        return {"error": f"缩略图生成失败: {e}"}


def _handle_dedup_check(db: Session, task: Task) -> dict:
    """重复照片检测（基于 MD5）"""
    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo or not photo.md5:
        return {"duplicates": 0}

    from app.crud.photo import get_photos_by_md5
    duplicates = get_photos_by_md5(db, photo.md5)
    dup_ids = [str(p.id) for p in duplicates if str(p.id) != str(task.photo_id)]

    return {"duplicates": len(dup_ids), "duplicate_ids": dup_ids}


def _handle_geocode(db: Session, task: Task) -> dict:
    """反向地理编码：GPS 经纬度 → 省/市/区，回填 PhotoMetadata"""
    from app.crud.photo import create_photo_metadata, update_processed_tasks
    from app.services.geocode_service import reverse_geocode

    photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
    if not photo:
        return {"error": "照片不存在"}

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


# 任务类型 → 处理器映射
HANDLERS = {
    TaskType.object_detection: _handle_object_detection,
    TaskType.image_embedding: _handle_image_embedding,
    TaskType.image_description: _handle_image_description,
    TaskType.quality_assessment: _handle_quality_assessment,
    TaskType.exif_extract: _handle_exif_extract,
    TaskType.face_detect: _handle_face_detect,
    TaskType.face_cluster: _handle_face_cluster,
    TaskType.thumbnail_generate: _handle_thumbnail_generate,
    TaskType.dedup_check: _handle_dedup_check,
    TaskType.geocode: _handle_geocode,
}


# ═══════════════════════════════════════════════════
# 主调度循环
# ═══════════════════════════════════════════════════


def _process_one_task(db: Session, task: Task) -> bool:
    """处理单个任务，返回是否成功"""
    handler = HANDLERS.get(getattr(task, 'task_type', None))
    if not handler:
        update_task_status(db, task, TaskStatus.completed,
                          result={"note": "该任务类型暂未实现处理器"})
        return True

    try:
        update_task_status(db, task, TaskStatus.running)
        result = handler(db, task)
        update_task_status(db, task, TaskStatus.completed, result=result)

        # 标记照片已完成该分析
        if task.photo_id:
            photo = db.query(Photo).filter(Photo.id == task.photo_id).first()
            if photo:
                task_type_name = task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type)
                update_processed_tasks(db, photo, task_type_name, result)

        logger.info(f"任务完成: {task.id} ({task.task_type.value if hasattr(task.task_type, 'value') else task.task_type})")
        return True

    except Exception as e:
        logger.error(f"任务失败: {task.id} - {e}")
        update_task_status(db, task, TaskStatus.failed, error_message=str(e))
        return False


def _worker_loop(poll_interval: int = 5, batch_size: int = 5):
    """后台循环：每隔 poll_interval 秒拉取 pending 任务并处理"""
    logger.info("任务 Worker 已启动")
    while not _stop_flag.is_set():
        try:
            db = SessionLocal()
            try:
                tasks = get_pending_tasks(db, limit=batch_size)
                if tasks:
                    logger.info(f"发现 {len(tasks)} 个待处理任务")
                    for task in tasks:
                        if _stop_flag.is_set():
                            break
                        _process_one_task(db, task)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Worker 异常: {e}")

        # 等待下一次轮询
        _stop_flag.wait(timeout=poll_interval)

    logger.info("任务 Worker 已停止")


def start_worker(poll_interval: int = 5, batch_size: int = 5):
    """启动后台任务 Worker（在 FastAPI lifespan 中调用）"""
    global _worker_thread, _stop_flag
    if _worker_thread and _worker_thread.is_alive():
        return

    _stop_flag.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        args=(poll_interval, batch_size),
        daemon=True,
    )
    _worker_thread.start()


def stop_worker():
    """停止后台任务 Worker"""
    global _worker_thread
    _stop_flag.set()
    if _worker_thread:
        _worker_thread.join(timeout=5)
