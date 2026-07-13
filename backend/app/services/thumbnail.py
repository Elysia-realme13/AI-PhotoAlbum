"""
缩略图生成服务
基于 Pillow 实现图片缩略图生成和尺寸获取
"""
import io
from PIL import Image

# 缩略图最大尺寸（保持宽高比，不超过此尺寸）
THUMBNAIL_SIZE = (400, 400)
THUMBNAIL_QUALITY = 85


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
