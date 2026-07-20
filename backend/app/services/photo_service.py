"""
照片上传服务

处理照片上传的完整业务流程:
    1. 接收文件 → 保存到存储 → 计算 MD5 → 去重检查
    2. 提取 EXIF 元数据（拍摄时间、GPS、相机型号等）
    3. 获取图片尺寸
    4. 创建 Photo + PhotoMetadata 记录
    5. 创建异步 AI 分析任务
"""

import hashlib
import logging
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

from fastapi import UploadFile
from PIL import Image
from PIL.ExifTags import Base as ExifBase
from sqlalchemy.orm import Session

from app.database.storage import storage
from app.models.photo import FileType
from app.models.task import TaskType
from app.services.thumbnail import generate_thumbnail_bytes, optimize_image_bytes

logger = logging.getLogger("app.services.photo")


# EXIF 标签映射: {ExifTags.Base 枚举值: PhotoMetadata 字段名}
# 参考: https://exiftool.org/TagNames/EXIF.html
EXIF_FIELD_MAP = {
    "Make": "camera_make",
    "Model": "camera_model",
    "LensModel": "lens_model",
    "FocalLength": "focal_length",
    "FNumber": "aperture",
    "ExposureTime": "shutter_speed",
    "ISOSpeedRatings": "iso",
    "GPSLatitude": None,      # 需要特殊处理（度分秒 → 十进制）
    "GPSLongitude": None,     # 需要特殊处理
    "GPSAltitude": "altitude",
}


def _compute_md5(content: bytes) -> str:
    """计算文件 MD5"""
    return hashlib.md5(content).hexdigest()


def _extract_exif(image: Image.Image) -> dict:
    """
    从 PIL Image 中提取 EXIF 数据

    Returns:
        dict: 与 PhotoMetadata 字段名对应的字典
    """
    exif_data = {}
    try:
        exif_raw = image._getexif()
        if not exif_raw:
            return exif_data

        for tag_id, value in exif_raw.items():
            tag_name = ExifBase(tag_id).name if tag_id in ExifBase.__members__.values() else None
            if not tag_name:
                continue

            if tag_name == "Make":
                exif_data["camera_make"] = str(value).strip("\x00") if value else None
            elif tag_name == "Model":
                exif_data["camera_model"] = str(value).strip("\x00") if value else None
            elif tag_name == "LensModel":
                exif_data["lens_model"] = str(value) if value else None
            elif tag_name == "FocalLength":
                exif_data["focal_length"] = float(value) if value else None
            elif tag_name == "FNumber":
                exif_data["aperture"] = float(value) if value else None
            elif tag_name == "ExposureTime":
                exif_data["shutter_speed"] = str(value) if value else None
            elif tag_name == "ISOSpeedRatings":
                exif_data["iso"] = int(value) if value else None

        # GPS 信息需要从 GPSInfo 标签获取
        gps_raw = image._getexif()
        if gps_raw:
            gps_info = gps_raw.get(0x8825)  # GPSInfo IFD
            if gps_info:
                lat = _parse_gps(gps_info, "N", "S")
                lon = _parse_gps(gps_info, "E", "W")
                if lat is not None:
                    exif_data["latitude"] = lat
                if lon is not None:
                    exif_data["longitude"] = lon
                if 6 in gps_info:  # GPSAltitude
                    alt = gps_info[6]
                    exif_data["altitude"] = float(alt) if not isinstance(alt, tuple) else float(alt[0]) / float(alt[1]) if alt[1] != 0 else None

    except Exception as e:
        logger.warning(f"EXIF 提取失败: {e}")

    return exif_data


def _parse_gps(gps_info: dict, pos_ref: str, neg_ref: str) -> Optional[float]:
    """将 GPS 度分秒转换为十进制"""
    ref_map = {"N": 1, "S": -1, "E": 1, "W": -1}
    try:
        if pos_ref == "N" or pos_ref == "S":
            ref_tag = 1 if pos_ref == "N" else 2
        else:
            ref_tag = 3 if pos_ref == "E" else 4

        ref = gps_info.get(ref_tag, pos_ref)
        sign = 1
        if isinstance(ref, str):
            sign = ref_map.get(ref, 1)

        coords = gps_info.get(ref_tag - 1 if ref_tag in (2, 4) else ref_tag + 1)
        if not coords:
            return None

        # 度分秒 → 十进制
        degrees = float(coords[0])
        minutes = float(coords[1]) / 60.0 if len(coords) > 1 else 0
        seconds = float(coords[2]) / 3600.0 if len(coords) > 2 else 0
        return sign * (degrees + minutes + seconds)

    except Exception:
        return None


def _extract_photo_time(exif_data: dict) -> Optional[datetime]:
    """从 EXIF 提取拍摄时间"""
    # PIL 可以读取 DateTimeOriginal (0x9003) 或 DateTimeDigitized (0x9004)
    # 简化处理：优先用 DateTimeOriginal
    try:
        raw = Image.open.__self__ if hasattr(Image.open, '__self__') else None
    except Exception:
        pass
    return None


def _get_image_dimensions(image: Image.Image) -> tuple:
    """获取图片尺寸，自动处理 EXIF 旋转"""
    width, height = image.size
    # 检查 EXIF 旋转标记 (0x0112)
    try:
        exif_raw = image._getexif()
        if exif_raw:
            orientation = exif_raw.get(0x0112, 1)
            if orientation in (5, 6, 7, 8):
                width, height = height, width  # 旋转后交换宽高
    except Exception:
        pass
    return width, height


async def upload_single_photo(
    db: Session,
    file: UploadFile,
    owner_id: uuid.UUID,
) -> dict:
    """
    上传单张照片的完整流程

    Args:
        db: 数据库会话
        file: 上传文件
        owner_id: 用户 ID

    Returns:
        dict: {
            "photo": Photo ORM 对象,
            "task_ids": [uuid, ...],
            "is_duplicate": bool,
            "skipped_md5": str or None,
        }
    """
    from app.crud.photo import (
        create_photo,
        create_photo_metadata,
        get_photos_by_md5,
    )
    from app.crud.task import create_tasks_batch

    # 1. 读取文件内容并计算 MD5
    content = await file.read()
    md5 = _compute_md5(content)

    # 2. 去重检查
    existing = get_photos_by_md5(db, md5)
    if existing:
        logger.info(f"MD5 重复，跳过: {file.filename} → {existing.filename}")
        return {
            "photo": existing,
            "task_ids": [],
            "is_duplicate": True,
            "skipped_md5": md5,
        }

    # 3. PIL 读取原始图片，提取 EXIF + 尺寸（在压缩前基于原始字节）
    width, height = None, None
    exif_data = {}
    photo_time = None
    orientation = 1

    try:
        image = Image.open(BytesIO(content))
        width, height = _get_image_dimensions(image)

        # 提取 EXIF
        exif_data = _extract_exif(image)

        # 读取方向标记与拍摄时间
        try:
            exif_raw = image._getexif()
            if exif_raw:
                orientation = exif_raw.get(0x0112, 1)
                # 0x9003 = DateTimeOriginal
                if 0x9003 in exif_raw:
                    dt_str = exif_raw[0x9003]  # "2025:07:14 16:30:00"
                    photo_time = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        except (ValueError, KeyError):
            pass

        image.close()
    except Exception as e:
        logger.warning(f"图片解析失败（可能是视频等其他格式）: {e}")

    # 4. 压缩原图（限制最长边 + 重编码，保留 EXIF）后落盘
    optimized_bytes, opt_w, opt_h = optimize_image_bytes(content)
    filename, file_path, file_size = await storage.save_image_bytes(
        file.filename or "unknown", optimized_bytes
    )

    # 以压缩后尺寸为准（应用 EXIF 方向交换，与展示保持一致）
    if opt_w and opt_h:
        if orientation in (5, 6, 7, 8):
            width, height = opt_h, opt_w
        else:
            width, height = opt_w, opt_h

    # 5. 生成并保存缩略图
    try:
        thumb_bytes = generate_thumbnail_bytes(optimized_bytes)
        await storage.save_thumbnail(filename, thumb_bytes)
    except Exception as e:
        logger.warning(f"缩略图生成失败: {e}")

    # 6. 创建 Photo 记录
    photo = create_photo(
        db=db,
        owner_id=owner_id,
        filename=filename,
        original_name=file.filename or "unknown",
        file_path=file_path,
        file_size=file_size,
        md5=md5,
        file_type=FileType.image.value,
        width=width,
        height=height,
        photo_time=photo_time or datetime.now(),
    )

    # 7. 创建 EXIF 元数据
    if exif_data:
        create_photo_metadata(db, photo_id=photo.id, **exif_data)

    # 8. 创建异步分析任务
    task_types = [
        TaskType.exif_extract,       # EXIF 提取
        TaskType.geocode,            # 反向地理编码 GPS → 省/市/区
        TaskType.object_detection,   # YOLO 目标检测 → 自动标签
        TaskType.face_detect,        # 人脸检测
        TaskType.image_description,  # AI 描述
        TaskType.image_embedding,    # CLIP 向量
        TaskType.quality_assessment, # 质量评分
    ]
    tasks = create_tasks_batch(db, owner_id=owner_id, photo_id=photo.id, task_types=task_types)

    # 9. 立即执行 YOLO 目标检测（写入 ImageDescription.tags，供后续搜索使用）
    from app.tasks import process_photo_detection
    for t in tasks:
        if t.task_type == TaskType.object_detection:
            process_photo_detection(
                photo_id=str(photo.id),
                image_path=file_path,
                task_id=str(t.id),
            )
            break

    return {
        "task_ids": [t.id for t in tasks],
        "is_duplicate": False,
        "skipped_md5": None,
    }
