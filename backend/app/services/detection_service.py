"""
YOLO 目标检测服务

使用 Ultralytics YOLO11（COCO 数据集训练）对图片进行目标检测。
支持检测 80 种 COCO 常见物体（人、车、动物、家具等）。

使用方式：
    pip install ultralytics  # 首次使用前安装
    from app.services.detection_service import detect_objects
    results = detect_objects("/path/to/image.jpg")
"""
import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── COCO 类别名称（YOLO 官方 80 类） ──────────────────────────────
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
]

# ── 全局模型缓存（避免每次调用重新加载） ─────────────────────────
_model = None
_model_name: Optional[str] = None

# 默认模型名称（可用 yolo11n.pt / yolo11s.pt / yolo11m.pt 等）
DEFAULT_MODEL = "yolo11n.pt"


def _get_model(model_name: str = DEFAULT_MODEL):
    """
    获取（缓存）YOLO 模型实例

    Args:
        model_name: 模型名称，如 yolo11n.pt / yolo11s.pt

    Returns:
        Ultralytics YOLO 模型实例，或 None（加载失败时）
    """
    global _model, _model_name

    if _model is not None and _model_name == model_name:
        return _model

    try:
        from ultralytics import YOLO

        logger.info(f"正在加载 YOLO 模型: {model_name} ...")
        _model = YOLO(model_name)
        _model_name = model_name
        logger.info(f"YOLO 模型加载完成: {model_name}")
        return _model
    except ImportError:
        logger.error(
            "ultralytics 未安装，请执行: pip install ultralytics"
        )
        return None
    except Exception as e:
        logger.error(f"YOLO 模型加载失败: {e}")
        return None


def detect_objects(
    image_path: str,
    confidence_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    model_name: str = DEFAULT_MODEL,
    max_detections: int = 100,
) -> dict:
    """
    对图片执行 YOLO 目标检测

    Args:
        image_path: 图片文件路径
        confidence_threshold: 置信度阈值（0-1），低于此值的检测结果会被过滤
        iou_threshold: NMS IoU 阈值
        model_name: YOLO 模型名称
        max_detections: 最大检测数

    Returns:
        {
            "success": bool,
            "detections": [
                {
                    "label": "person",
                    "confidence": 0.92,
                    "bbox_x": 0.5,      # 归一化中心坐标
                    "bbox_y": 0.3,
                    "bbox_w": 0.2,
                    "bbox_h": 0.4,
                    "class_id": 0,
                },
                ...
            ],
            "image_width": int,
            "image_height": int,
            "total": int,
            "model": str,
            "error": str | None,
        }
    """
    result = {
        "success": False,
        "detections": [],
        "image_width": 0,
        "image_height": 0,
        "total": 0,
        "model": model_name,
        "error": None,
    }

    # ── 检查文件 ──────────────────────────────────────────────
    img_path = Path(image_path)
    if not img_path.exists():
        result["error"] = f"图片文件不存在: {image_path}"
        return result

    # ── 加载模型 ──────────────────────────────────────────────
    model = _get_model(model_name)
    if model is None:
        result["error"] = "YOLO 模型加载失败"
        return result

    # ── 执行推理 ──────────────────────────────────────────────
    try:
        predictions = model(
            source=str(img_path),
            conf=confidence_threshold,
            iou=iou_threshold,
            max_det=max_detections,
            verbose=False,
        )
    except Exception as e:
        logger.error(f"YOLO 推理失败: {e}")
        result["error"] = f"推理失败: {e}"
        return result

    # ── 解析结果 ──────────────────────────────────────────────
    if not predictions or len(predictions) == 0:
        result["success"] = True
        return result

    pred = predictions[0]

    # 图片尺寸
    if hasattr(pred, "orig_shape") and pred.orig_shape:
        result["image_height"] = pred.orig_shape[0]
        result["image_width"] = pred.orig_shape[1]

    # 检测框
    if pred.boxes is None or len(pred.boxes) == 0:
        result["success"] = True
        return result

    boxes = pred.boxes
    img_h = result["image_height"] or 1
    img_w = result["image_width"] or 1

    for i in range(len(boxes)):
        try:
            # xyxy → 归一化中心坐标 + 宽高
            xyxy = boxes.xyxy[i].tolist()
            x1, y1, x2, y2 = xyxy

            box_w = x2 - x1
            box_h = y2 - y1
            cx = x1 + box_w / 2
            cy = y1 + box_h / 2

            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            label = COCO_CLASSES[cls_id] if 0 <= cls_id < len(COCO_CLASSES) else f"class_{cls_id}"

            result["detections"].append({
                "label": label,
                "confidence": round(conf, 4),
                "bbox_x": round(cx / img_w, 6),
                "bbox_y": round(cy / img_h, 6),
                "bbox_w": round(box_w / img_w, 6),
                "bbox_h": round(box_h / img_h, 6),
                "class_id": cls_id,
            })
        except Exception as e:
            logger.warning(f"解析第 {i} 个检测框时出错: {e}")
            continue

    result["total"] = len(result["detections"])
    result["success"] = True
    return result


def detect_objects_from_bytes(
    image_bytes: bytes,
    confidence_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    model_name: str = DEFAULT_MODEL,
    max_detections: int = 100,
) -> dict:
    """
    对图片字节数据执行 YOLO 目标检测（不需先存文件）

    Args:
        image_bytes: 图片的字节数据
        其余参数同 detect_objects()

    Returns:
        同 detect_objects()
    """
    result = {
        "success": False,
        "detections": [],
        "image_width": 0,
        "image_height": 0,
        "total": 0,
        "model": model_name,
        "error": None,
    }

    model = _get_model(model_name)
    if model is None:
        result["error"] = "YOLO 模型加载失败"
        return result

    try:
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        img_np = np.array(img)

        predictions = model(
            source=img_np,
            conf=confidence_threshold,
            iou=iou_threshold,
            max_det=max_detections,
            verbose=False,
        )
    except ImportError:
        result["error"] = "缺少依赖: numpy 或 Pillow"
        return result
    except Exception as e:
        logger.error(f"YOLO 推理失败: {e}")
        result["error"] = f"推理失败: {e}"
        return result

    if not predictions or len(predictions) == 0:
        result["success"] = True
        return result

    pred = predictions[0]

    if hasattr(pred, "orig_shape") and pred.orig_shape:
        result["image_height"] = pred.orig_shape[0]
        result["image_width"] = pred.orig_shape[1]

    if pred.boxes is None or len(pred.boxes) == 0:
        result["success"] = True
        return result

    boxes = pred.boxes
    img_h = result["image_height"] or 1
    img_w = result["image_width"] or 1

    for i in range(len(boxes)):
        try:
            xyxy = boxes.xyxy[i].tolist()
            x1, y1, x2, y2 = xyxy
            box_w = x2 - x1
            box_h = y2 - y1
            cx = x1 + box_w / 2
            cy = y1 + box_h / 2

            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            label = COCO_CLASSES[cls_id] if 0 <= cls_id < len(COCO_CLASSES) else f"class_{cls_id}"

            result["detections"].append({
                "label": label,
                "confidence": round(conf, 4),
                "bbox_x": round(cx / img_w, 6),
                "bbox_y": round(cy / img_h, 6),
                "bbox_w": round(box_w / img_w, 6),
                "bbox_h": round(box_h / img_h, 6),
                "class_id": cls_id,
            })
        except Exception as e:
            logger.warning(f"解析第 {i} 个检测框时出错: {e}")
            continue

    result["total"] = len(result["detections"])
    result["success"] = True
    return result


def get_detection_summary(detections: list) -> list:
    """
    对检测结果进行去重汇总统计

    Args:
        detections: detect_objects() 返回的 detections 列表

    Returns:
        [{"label": "person", "count": 3, "max_confidence": 0.95}, ...]
    """
    summary = {}
    for d in detections:
        label = d["label"]
        if label not in summary:
            summary[label] = {"label": label, "count": 0, "max_confidence": 0.0}
        summary[label]["count"] += 1
        summary[label]["max_confidence"] = max(summary[label]["max_confidence"], d["confidence"])

    return sorted(summary.values(), key=lambda x: -x["count"])


def draw_detections(
    image_path: str,
    detections: list,
    output_path: Optional[str] = None,
) -> Optional[bytes]:
    """
    在图片上绘制检测框并返回标注后的图片

    Args:
        image_path: 原图路径
        detections: detect_objects() 返回的 detections 列表
        output_path: 如果指定，将结果保存到此路径

    Returns:
        标注后的图片字节数据（JPEG 格式），或 None（失败时）
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        img_w, img_h = img.size

        # 尝试加载字体（系统字体或默认）
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except (IOError, OSError):
            try:
                font = ImageFont.truetype(
                    "C:/Windows/Fonts/msyh.ttc", 16
                )
            except (IOError, OSError):
                font = ImageFont.load_default()

        # 为不同类别分配颜色（基于 class_id 哈希）
        import hashlib

        def _color_for_class(cls_id: int):
            h = hashlib.md5(str(cls_id).encode()).hexdigest()
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return (r, g, b)

        for d in detections:
            cx = d["bbox_x"] * img_w
            cy = d["bbox_y"] * img_h
            bw = d["bbox_w"] * img_w
            bh = d["bbox_h"] * img_h

            x1 = cx - bw / 2
            y1 = cy - bh / 2
            x2 = cx + bw / 2
            y2 = cy + bh / 2

            color = _color_for_class(d.get("class_id", 0))

            # 画框
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            # 画标签背景
            label_text = f"{d['label']} {d['confidence']:.2f}"
            bbox = draw.textbbox((0, 0), label_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.rectangle(
                [x1, y1 - text_h - 4, x1 + text_w + 8, y1],
                fill=color,
            )
            draw.text((x1 + 4, y1 - text_h - 2), label_text, fill="white", font=font)

        if output_path:
            img.save(output_path, "JPEG", quality=90)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    except ImportError as e:
        logger.error(f"绘图依赖缺失: {e}")
        return None
    except Exception as e:
        logger.error(f"绘制检测框失败: {e}")
        return None


__all__ = [
    "detect_objects",
    "detect_objects_from_bytes",
    "get_detection_summary",
    "draw_detections",
    "COCO_CLASSES",
    "DEFAULT_MODEL",
]
