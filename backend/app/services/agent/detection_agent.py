"""Detection Agent --- YOLO-powered object detection specialist agent.

Responsibilities:
  - Detect objects in a specific set of photos (by YOLO tags or real-time inference)
  - Analyze a newly uploaded image with YOLO + CLIP
  - Return structured detection summaries to the Supervisor
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from langchain_core.tools import tool

from app.models.description import ImageDescription
from app.services.detection_service import (
    detect_objects_from_bytes,
    get_detection_summary,
    get_model_class_names,
    # COCO_CLASSES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Detection agent tool
# ---------------------------------------------------------------------------

@tool
def detect_objects_in_photos(
    photo_ids: List[str],
    target_objects: List[str],
    db_session_info: Optional[dict] = None,
) -> dict:
    """Check whether a list of photo IDs contain specific YOLO-detectable objects.

    Uses pre-computed YOLO tags from ImageDescription.tags (offline mode).
    Falls back to real-time YOLO inference only when tags are missing and image bytes are available.

    Args:
        photo_ids: List of photo UUID strings to check.
        target_objects: List of object labels to look for, e.g. ["dog", "cat", "car"].
                       Must be COCO-80 class names (lowercase English).

    Returns:
        {"found": int, "photos": [{"photo_id": str, "matched_objects": [str], ...}]}
    """
    pass  # implemented in run_detection_agent


def _yolo_tag_filter(
    db: Session,
    photo_ids: List[str],
    target_objects: List[str],
) -> List[dict]:
    """Filter photos by YOLO tags in ImageDescription."""
    pids = [UUID(pid) for pid in photo_ids]
    rows = (
        db.query(ImageDescription.photo_id, ImageDescription.tags)
        .filter(
            ImageDescription.photo_id.in_(pids),
            ImageDescription.tags.isnot(None),
        )
        .all()
    )
    tag_map = {str(r.photo_id): r.tags for r in rows}

    results = []
    for pid in photo_ids:
        tags = tag_map.get(pid)
        labels = set()
        if isinstance(tags, dict):
            # 规范结构：{"summary": [{"label": ...}], ...}
            for item in tags.get("summary", []) or []:
                if isinstance(item, dict) and item.get("label"):
                    labels.add(item["label"].lower())
        elif isinstance(tags, list):
            # 兼容旧结构：字符串列表或 dict 列表
            for t in tags:
                if isinstance(t, dict) and t.get("label"):
                    labels.add(t["label"].lower())
                elif isinstance(t, str):
                    labels.add(t.lower())
        matched = [o for o in target_objects if o.lower() in labels]
        if matched:
            results.append({"photo_id": pid, "matched_objects": matched})
    return results


def run_detection_agent(
    photo_ids: List[str],
    target_objects: List[str],
    db: Session,
    image_bytes: Optional[bytes] = None,
) -> Dict[str, Any]:
    """Entry point for the Detection Agent.

    Args:
        photo_ids: Photo UUIDs to inspect.
        target_objects: Object labels (COCO-80).
        db: Database session.
        image_bytes: Optional raw image for real-time YOLO.

    Returns:
        {"found": int, "photos": list, "detections": list}
    """
    if not target_objects:
        return {"found": 0, "photos": [], "detections": []}

    # Validate against COCO classes
    class_names = get_model_class_names()
    invalid = [o for o in target_objects if o.lower() not in class_names]
    if invalid:
        logger.warning(f"Unknown object(s) ignored: {invalid}")
        
    valid_objects = [o for o in target_objects if o.lower() in class_names]
    if not valid_objects:
        return {"found": 0, "photos": [], "detections": []}

    # Phase 1: tag-based filtering (fast, offline)
    tag_matches = _yolo_tag_filter(db, photo_ids, valid_objects)

    # Phase 2: real-time YOLO for unmatched photo IDs (if image_bytes provided)
    live_matches = []
    already_matched = {m["photo_id"] for m in tag_matches}
    unmatched = [pid for pid in photo_ids if pid not in already_matched]

    if unmatched and image_bytes:
        try:
            det_result = detect_objects_from_bytes(image_bytes, confidence_threshold=0.25)
            if det_result.get("success"):
                summary = get_detection_summary(det_result["detections"])
                found_labels = {s["label"].lower() for s in summary}
                matched = [o for o in valid_objects if o.lower() in found_labels]
                if matched:
                    live_matches.append({
                        "photo_id": unmatched[0] if len(unmatched) == 1 else "live_image",
                        "matched_objects": matched,
                        "source": "real-time YOLO",
                        "summary": [
                            {"label": s["label"], "count": s["count"], "confidence": round(s["max_confidence"], 2)}
                            for s in summary
                        ],
                    })
        except Exception as e:
            logger.error(f"Real-time YOLO failed: {e}")

    all_matches = tag_matches + live_matches

    return {
        "found": len(all_matches),
        "photos": all_matches,
        "target_objects": valid_objects,
    }


__all__ = [
    "detect_objects_in_photos",
    "run_detection_agent",
    "get_model_class_names",
    # "COCO_CLASSES",
]