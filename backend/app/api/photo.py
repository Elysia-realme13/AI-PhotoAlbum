"""
照片 API 路由

所有接口均返回 BaseResponse 格式，需要认证的接口依赖 get_required_user。
"""

import uuid
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_required_user, get_current_user
from app.models.user import User
from app.models.photo import Photo

from app.schemas.response import BaseResponse, PaginatedData
from app.schemas.photo import (
    PhotoDetailResponse,
    PhotoListItem,
    PhotoUpdateRequest,
    ReanalyzeRequest,
    BatchPhotoRequest,
    BatchUploadResponse,
    UploadResult,
    TimelineGroup,
    MapPhotoItem,
)

from app.crud import photo as photo_crud
from app.services.photo_service import upload_single_photo

logger = logging.getLogger("app.api.photo")

router = APIRouter(prefix="/api/photos", tags=["照片"])


# ═══════════════════════════════════════════════════
# 照片上传
# ═══════════════════════════════════════════════════

@router.post("/upload", response_model=BaseResponse[BatchUploadResponse])
async def upload_photos(
    files: List[UploadFile] = File(..., description="照片文件，支持批量上传"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    上传照片（支持批量）

    流程：保存文件 → 提取 EXIF → MD5 去重 → 创建记录 → 创建 AI 分析任务

    - 支持格式: JPG, PNG, HEIC, GIF, WebP
    - 单文件最大 50MB（由 settings.MAX_UPLOAD_SIZE_MB 控制，Nginx 层截断）
    - MD5 重复的照片自动跳过，不计入 uploaded 数量
    """
    results = BatchUploadResponse()

    for file in files:
        try:
            result = await upload_single_photo(db, file, current_user.id)

            if result["is_duplicate"]:
                results.total_skipped += 1
                results.skipped_md5.append(result["skipped_md5"])
                continue

            photo = result["photo"]
            # 构造列表项（简化版，不含嵌套数据）
            results.photos.append(UploadResult(
                photo=PhotoListItem(
                    id=str(photo.id),
                    filename=photo.filename,
                    original_name=photo.original_name,
                    width=photo.width,
                    height=photo.height,
                    photo_time=photo.photo_time,
                    upload_time=photo.upload_time,
                    file_type=photo.file_type.value if hasattr(photo.file_type, 'value') else photo.file_type,
                    file_size=photo.file_size,
                    is_deleted=photo.is_deleted,
                ),
                task_ids=[str(tid) for tid in result["task_ids"]],
            ))
            results.total_uploaded += 1

        except Exception as e:
            logger.error(f"上传失败: {file.filename}, 错误: {e}")
            # 单张失败不影响其他照片
            continue

    return BaseResponse(data=results)


# ═══════════════════════════════════════════════════
# 照片查询
# ═══════════════════════════════════════════════════

@router.get("", response_model=BaseResponse[PaginatedData])
def list_photos(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=200, description="每页数量"),
    sort_by: str = Query(default="photo_time", description="排序字段：photo_time/upload_time/file_size"),
    order: str = Query(default="desc", pattern="^(asc|desc)$", description="排序方向"),
    file_type: Optional[str] = Query(default=None, description="文件类型：image/video"),
    date_from: Optional[datetime] = Query(default=None, description="拍摄时间起始"),
    date_to: Optional[datetime] = Query(default=None, description="拍摄时间截止"),
    album_id: Optional[str] = Query(default=None, description="按相册筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    照片列表（分页 + 多维度筛选）

    支持按时间范围、文件类型、相册筛选，以及多种排序方式。
    列表项仅返回缩略信息，不含 AI 描述和人脸等嵌套数据以减少传输量。
    """
    album_uuid = uuid.UUID(album_id) if album_id else None

    photos, total = photo_crud.get_photo_list(
        db=db,
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order,
        file_type=file_type,
        date_from=date_from,
        date_to=date_to,
        album_id=album_uuid,
        is_deleted=False,
    )

    items = []
    for p in photos:
        # 从 image_description 关联获取标签和评分（如果已分析）
        tags = None
        quality_score = None
        if p.image_description:
            tags = p.image_description.tags
            quality_score = p.image_description.quality_score

        items.append(PhotoListItem(
            id=str(p.id),
            filename=p.filename,
            original_name=p.original_name,
            width=p.width,
            height=p.height,
            photo_time=p.photo_time,
            upload_time=p.upload_time,
            file_type=p.file_type.value if hasattr(p.file_type, 'value') else str(p.file_type),
            file_size=p.file_size,
            is_deleted=p.is_deleted,
            tags=tags,
            quality_score=quality_score,
        ))

    return BaseResponse(data=PaginatedData(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    ))


@router.get("/{photo_id}", response_model=BaseResponse[PhotoDetailResponse])
def get_photo_detail(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    照片详情

    返回照片全部信息：基础字段 + EXIF 元数据 + AI 描述 + 人脸框列表。
    """
    photo = photo_crud.get_photo_detail(db, uuid.UUID(photo_id), owner_id=current_user.id)
    if not photo:
        return BaseResponse(code=404, msg="照片不存在", data=None)

    # 手动构建嵌套响应（因为 Pydantic from_attributes 不处理深层嵌套）
    detail = PhotoDetailResponse(
        id=str(photo.id),
        filename=photo.filename,
        original_name=photo.original_name,
        file_path=photo.file_path,
        file_size=photo.file_size,
        width=photo.width,
        height=photo.height,
        photo_time=photo.photo_time,
        upload_time=photo.upload_time,
        file_type=photo.file_type.value if hasattr(photo.file_type, 'value') else str(photo.file_type),
        md5=photo.md5,
        is_deleted=photo.is_deleted,
        processed_tasks=photo.processed_tasks,
    )

    # 元数据
    if photo.metadata_info:
        detail.metadata = {
            "camera_make": photo.metadata_info.camera_make,
            "camera_model": photo.metadata_info.camera_model,
            "lens_model": photo.metadata_info.lens_model,
            "focal_length": photo.metadata_info.focal_length,
            "aperture": photo.metadata_info.aperture,
            "shutter_speed": photo.metadata_info.shutter_speed,
            "iso": photo.metadata_info.iso,
            "latitude": photo.metadata_info.latitude,
            "longitude": photo.metadata_info.longitude,
            "altitude": photo.metadata_info.altitude,
            "country": photo.metadata_info.country,
            "province": photo.metadata_info.province,
            "city": photo.metadata_info.city,
            "district": photo.metadata_info.district,
            "address": photo.metadata_info.address,
        }

    # AI 描述
    if photo.image_description:
        detail.description = {
            "description": photo.image_description.description,
            "narrative": photo.image_description.narrative,
            "tags": photo.image_description.tags,
            "quality_score": photo.image_description.quality_score,
            "memory_score": photo.image_description.memory_score,
        }

    # 人脸框
    for face in (photo.faces or []):
        identity_name = face.identity.identity_name if face.identity else None
        detail.faces.append({
            "id": face.id,
            "face_identity_id": str(face.face_identity_id) if face.face_identity_id else None,
            "identity_name": identity_name,
            "face_rect": face.face_rect,
            "confidence": float(face.confidence) if face.confidence else None,
        })

    return BaseResponse(data=detail)


# ═══════════════════════════════════════════════════
# 文件服务（缩略图 / 原图）
# ═══════════════════════════════════════════════════

@router.get("/{photo_id}/file")
def get_photo_file(
    photo_id: str,
    download: bool = Query(default=False, description="是否触发浏览器下载"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    获取原图文件

    - ?download=false → 浏览器内嵌显示
    - ?download=true  → 触发文件下载
    """
    photo = photo_crud.get_photo_by_id(db, uuid.UUID(photo_id), owner_id=current_user.id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    import os
    if not os.path.exists(photo.file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 推断 MIME 类型
    ext = os.path.splitext(photo.file_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".heic": "image/heic",
        ".heif": "image/heif", ".bmp": "image/bmp",
    }
    media_type = mime_map.get(ext, "application/octet-stream")

    disposition = "attachment" if download else "inline"
    filename = photo.original_name or photo.filename

    return FileResponse(
        path=photo.file_path,
        media_type=media_type,
        filename=filename,
        content_disposition_type=disposition,
    )


@router.get("/{photo_id}/thumbnail")
def get_photo_thumbnail(
    photo_id: str,
    size: str = Query(default="medium", pattern="^(small|medium|large)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    获取缩略图

    TODO: Phase 2 后续实现缩略图生成，当前直接返回原图。
    计划尺寸: small=200px, medium=400px, large=800px（长边）。

    实现方式:
        1. 上传时由 thumbnail_generate 任务异步生成多尺寸缩略图
        2. 存储到 data/thumbnails/{photo_id}_{size}.jpg
        3. 此接口根据 size 参数返回对应文件
    """
    # 暂时回退到原图
    return get_photo_file(photo_id, download=False, db=db, current_user=current_user)


# ═══════════════════════════════════════════════════
# 照片操作
# ═══════════════════════════════════════════════════

@router.patch("/{photo_id}", response_model=BaseResponse[PhotoDetailResponse])
def update_photo(
    photo_id: str,
    data: PhotoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """修改照片属性（如修正拍摄时间）"""
    photo = photo_crud.get_photo_by_id(db, uuid.UUID(photo_id), owner_id=current_user.id)
    if not photo:
        return BaseResponse(code=404, msg="照片不存在", data=None)

    update_kwargs = {}
    if data.photo_time is not None:
        update_kwargs["photo_time"] = data.photo_time
    if data.original_name is not None:
        update_kwargs["original_name"] = data.original_name

    photo = photo_crud.update_photo(db, photo, **update_kwargs)
    return BaseResponse(data=_build_basic_response(photo))


@router.delete("/{photo_id}", response_model=BaseResponse[PhotoDetailResponse])
def delete_photo(
    photo_id: str,
    permanent: bool = Query(default=False, description="true=永久删除，false=移入回收站"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    删除照片

    - permanent=false → 软删除（移入回收站，可恢复）
    - permanent=true  → 物理删除（删除文件和数据库记录，不可恢复）
    """
    photo = photo_crud.get_photo_by_id(db, uuid.UUID(photo_id), owner_id=current_user.id, include_deleted=True)
    if not photo:
        return BaseResponse(code=404, msg="照片不存在", data=None)

    if permanent:
        # 物理删除：先删文件，再删记录
        import os
        from app.database.storage import storage
        if os.path.exists(photo.file_path):
            storage.delete_file(photo.file_path)
        photo_crud.permanent_delete_photo(db, photo)
        return BaseResponse(msg="照片已永久删除", data=None)
    else:
        photo = photo_crud.soft_delete_photo(db, photo)
        return BaseResponse(msg="照片已移入回收站", data=_build_basic_response(photo))


@router.post("/{photo_id}/restore", response_model=BaseResponse[PhotoDetailResponse])
def restore_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """从回收站恢复照片"""
    photo = photo_crud.get_photo_by_id(db, uuid.UUID(photo_id), owner_id=current_user.id, include_deleted=True)
    if not photo:
        return BaseResponse(code=404, msg="照片不存在", data=None)
    if not photo.is_deleted:
        return BaseResponse(code=400, msg="照片不在回收站中", data=None)

    photo = photo_crud.restore_photo(db, photo)
    return BaseResponse(msg="照片已恢复", data=_build_basic_response(photo))


# ═══════════════════════════════════════════════════
# 批量操作
# ═══════════════════════════════════════════════════

@router.post("/batch", response_model=BaseResponse[PaginatedData])
def batch_get_photos(
    req: BatchPhotoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    批量获取照片（用于相册详情页加载所有照片缩略图）

    与 GET /api/photos 的区别：通过 POST body 传递 photo_id 列表，
    避免 URL 过长导致 414 错误。
    """
    photo_ids = [uuid.UUID(pid) for pid in req.photo_ids]
    photos = photo_crud.get_photos_by_ids(db, photo_ids, owner_id=current_user.id)

    items = [_build_list_item(p) for p in photos]
    return BaseResponse(data=PaginatedData(
        total=len(items),
        page=1,
        page_size=len(items),
        items=items,
    ))


# ═══════════════════════════════════════════════════
# AI 分析触发
# ═══════════════════════════════════════════════════

@router.post("/{photo_id}/reanalyze", response_model=BaseResponse[dict])
def reanalyze_photo(
    photo_id: str,
    req: ReanalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    手动触发重新 AI 分析

    对已分析过的照片重新执行指定的分析任务。
    返回新创建的任务 ID 列表。
    """
    from app.models.task import TaskType
    from app.crud.task import create_tasks_batch

    photo = photo_crud.get_photo_by_id(db, uuid.UUID(photo_id), owner_id=current_user.id)
    if not photo:
        return BaseResponse(code=404, msg="照片不存在", data=None)

    # 校验任务类型
    valid_types = {t.value for t in TaskType}
    task_types = []
    for t_name in req.tasks:
        if t_name not in valid_types:
            return BaseResponse(code=400, msg=f"无效的任务类型: {t_name}", data=None)
        task_types.append(TaskType(t_name))

    tasks = create_tasks_batch(db, owner_id=current_user.id, photo_id=photo.id, task_types=task_types)

    return BaseResponse(data={
        "photo_id": str(photo.id),
        "tasks": [{"task_id": str(t.id), "task_type": t.task_type.value} for t in tasks],
    })


# ═══════════════════════════════════════════════════
# 时间轴
# ═══════════════════════════════════════════════════

@router.get("/timeline/list", response_model=BaseResponse[List[TimelineGroup]])
def get_timeline(
    group_by: str = Query(default="month", pattern="^(year|month|day)$", description="分组粒度"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    照片时间轴

    按年/月/日聚合照片数量，每组的 cover_photo 为该组第一张照片。
    前端可据此渲染类似 Google Photos 的时间轴瀑布流。
    """
    groups = photo_crud.get_timeline_groups(db, current_user.id, group_by=group_by)

    result = []
    for g in groups:
        cover = None
        if g.get("cover_photo_id"):
            cover_photo = photo_crud.get_photo_by_id(db, g["cover_photo_id"])
            if cover_photo:
                cover = _build_list_item(cover_photo)
        result.append(TimelineGroup(
            date=g["date"],
            count=g["count"],
            cover_photo=cover,
        ))

    return BaseResponse(data=result)


# ═══════════════════════════════════════════════════
# 地图视图
# ═══════════════════════════════════════════════════

@router.get("/map/list", response_model=BaseResponse[List[MapPhotoItem]])
def get_map_photos(
    sw_lat: Optional[float] = Query(default=None, description="视口西南角纬度"),
    sw_lng: Optional[float] = Query(default=None, description="视口西南角经度"),
    ne_lat: Optional[float] = Query(default=None, description="视口东北角纬度"),
    ne_lng: Optional[float] = Query(default=None, description="视口东北角经度"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """
    地图视图照片

    返回有 GPS 坐标的照片，用于地图页展示。
    可选传入视口范围 bounds 做空间筛选。
    """
    photos = photo_crud.get_map_photos(
        db, current_user.id,
        sw_lat=sw_lat, sw_lng=sw_lng,
        ne_lat=ne_lat, ne_lng=ne_lng,
    )

    items = []
    for p in photos:
        lat = p.metadata_info.latitude if p.metadata_info else None
        lng = p.metadata_info.longitude if p.metadata_info else None
        if lat is None or lng is None:
            continue
        items.append(MapPhotoItem(
            id=str(p.id),
            latitude=lat,
            longitude=lng,
            photo_time=p.photo_time,
            # TODO: 缩略图 URL 待 Phase 2 缩略图实现后替换
            thumbnail_url=f"/api/photos/{p.id}/thumbnail?size=small",
        ))

    return BaseResponse(data=items)


# ═══════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════

def _build_list_item(photo: Photo) -> PhotoListItem:
    """从 ORM 对象构建列表项响应"""
    tags = None
    quality_score = None
    if photo.image_description:
        tags = photo.image_description.tags
        quality_score = photo.image_description.quality_score

    return PhotoListItem(
        id=str(photo.id),
        filename=photo.filename,
        original_name=photo.original_name,
        width=photo.width,
        height=photo.height,
        photo_time=photo.photo_time,
        upload_time=photo.upload_time,
        file_type=photo.file_type.value if hasattr(photo.file_type, 'value') else str(photo.file_type),
        file_size=photo.file_size,
        is_deleted=photo.is_deleted,
        tags=tags,
        quality_score=quality_score,
    )


def _build_basic_response(photo: Photo) -> PhotoDetailResponse:
    """从 ORM 对象构建基础响应（不含嵌套数据）"""
    return PhotoDetailResponse(
        id=str(photo.id),
        filename=photo.filename,
        original_name=photo.original_name,
        file_path=photo.file_path,
        file_size=photo.file_size,
        width=photo.width,
        height=photo.height,
        photo_time=photo.photo_time,
        upload_time=photo.upload_time,
        file_type=photo.file_type.value if hasattr(photo.file_type, 'value') else str(photo.file_type),
        md5=photo.md5,
        is_deleted=photo.is_deleted,
        processed_tasks=photo.processed_tasks,
    )
