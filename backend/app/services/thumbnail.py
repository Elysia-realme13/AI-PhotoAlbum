"""
缩略图生成服务
基于 Pillow 实现图片缩略图生成和尺寸获取
"""
import io
import logging

from PIL import Image

from app.config.settings import settings

logger = logging.getLogger("app.services.thumbnail")

# 缩略图最大尺寸（保持宽高比，不超过此尺寸）
THUMBNAIL_SIZE = (400, 400)
THUMBNAIL_QUALITY = 85

# 支持重编码压缩的图片格式（Pillow format 名称）
_OPTIMIZABLE_FORMATS = {"JPEG", "PNG", "WEBP"}


def generate_thumbnail_bytes(image_bytes: bytes) -> bytes:
    """
    从原始图片字节生成缩略图字节

    Args:
        image_bytes: 原始图片的字节数据

    Returns:
        JPEG 格式的缩略图字节数据
    """
    img = Image.open(io.BytesIO(image_bytes))

    # HEIC 等格式可能需要转换模式
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')

    # 生成缩略图（保持宽高比）
    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

    # RGBA → RGB（JPEG 不支持透明通道）
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    output = io.BytesIO()
    img.save(output, format='JPEG', quality=THUMBNAIL_QUALITY)
    return output.getvalue()


def get_image_dimensions(file_path: str) -> tuple[int, int]:
    """
    获取图片文件的实际宽高

    Args:
        file_path: 图片文件路径

    Returns:
        (width, height)
    """
    with Image.open(file_path) as img:
        return img.size


def get_image_dimensions_from_bytes(image_bytes: bytes) -> tuple[int, int]:
    """
    从字节数据获取图片宽高

    Args:
        image_bytes: 图片字节数据

    Returns:
        (width, height)
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        return img.size


def optimize_image_bytes(image_bytes: bytes) -> tuple[bytes, int, int]:
    """
    压缩原图：仅限制最长边 + 重编码，完整保留 EXIF/ICC 信息。

    - 仅处理 JPEG/PNG/WebP 静态图；GIF（可能为动图）、其他/无法解析格式一律原样返回。
    - 最长边超过 settings.MAX_IMAGE_LONG_EDGE 时按比例 LANCZOS 缩放，否则不缩放仅重编码。
    - 不做 exif_transpose，保持 EXIF 方向标记原样，避免改变照片原本信息。
    - 若重编码结果不比原图小，则返回原字节（避免反向增大）。

    Returns:
        (处理后字节, width, height)。无法处理时返回 (原字节, 原宽, 原高)。
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.warning(f"图片解析失败，跳过压缩: {e}")
        return image_bytes, 0, 0

    fmt = (img.format or "").upper()
    orig_w, orig_h = img.size

    if fmt not in _OPTIMIZABLE_FORMATS:
        # 动图/视频/未知格式：原样返回
        return image_bytes, orig_w, orig_h

    # 保留原始元数据
    exif = img.info.get("exif")
    icc = img.info.get("icc_profile")

    # 等比缩放（仅缩小，不放大）
    max_edge = settings.MAX_IMAGE_LONG_EDGE
    if max(orig_w, orig_h) > max_edge:
        img.thumbnail((max_edge, max_edge), Image.LANCZOS)

    new_w, new_h = img.size

    save_kwargs = {}
    if exif:
        save_kwargs["exif"] = exif
    if icc:
        save_kwargs["icc_profile"] = icc

    if fmt == "PNG":
        save_kwargs["optimize"] = True
    elif fmt == "WEBP":
        save_kwargs["quality"] = settings.IMAGE_QUALITY
        save_kwargs["method"] = 6
    else:  # JPEG
        # JPEG 不支持透明通道
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        save_kwargs["quality"] = settings.IMAGE_QUALITY
        save_kwargs["optimize"] = True
        save_kwargs["progressive"] = True

    try:
        output = io.BytesIO()
        img.save(output, format=fmt, **save_kwargs)
        new_bytes = output.getvalue()
    except Exception as e:
        logger.warning(f"图片重编码失败，保留原图: {e}")
        return image_bytes, orig_w, orig_h

    # 结果不比原图小则放弃压缩（但缩放过尺寸仍以处理后尺寸为准）
    if len(new_bytes) >= len(image_bytes) and (new_w, new_h) == (orig_w, orig_h):
        return image_bytes, orig_w, orig_h

    return new_bytes, new_w, new_h
