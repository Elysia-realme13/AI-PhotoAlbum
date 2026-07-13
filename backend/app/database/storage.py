"""
文件存储模块
支持本地文件存储和 MinIO（可选）
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
import aiofiles
from app.config.settings import settings


class LocalStorage:
    """本地文件存储"""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.thumbnail_dir = Path(settings.THUMBNAIL_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, original_name: str) -> str:
        """生成唯一文件名"""
        ext = Path(original_name).suffix.lower()
        return f"{uuid.uuid4().hex}{ext}"

    async def save_upload_bytes(self, filename: str, content: bytes) -> tuple[str, str, int]:
        """
        直接保存文件字节

        Args:
            filename: 目标文件名
            content: 文件字节数据

        Returns:
            (filename, file_path, file_size)
        """
        file_path = self.upload_dir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        return filename, str(file_path), len(content)

    async def save_upload(self, file: UploadFile) -> tuple[str, str, int]:
        """
        保存上传文件（从 UploadFile 读取）
        Returns: (filename, file_path, file_size)
        """
        filename = self._generate_filename(file.filename or "unknown")
        file_path = self.upload_dir / filename

        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return filename, str(file_path), len(content)

    def get_absolute_path(self, file_path: str) -> Path:
        """获取文件的绝对路径"""
        return Path(file_path)

    def delete_file(self, file_path: str):
        """删除文件"""
        path = Path(file_path)
        if path.exists():
            path.unlink()

    async def save_thumbnail(self, photo_id: str, image_bytes: bytes) -> str:
        """保存缩略图，返回路径"""
        thumb_path = self.thumbnail_dir / f"{photo_id}_thumb.jpg"
        async with aiofiles.open(thumb_path, "wb") as f:
            await f.write(image_bytes)
        return str(thumb_path)


# 全局存储实例
storage = LocalStorage()
