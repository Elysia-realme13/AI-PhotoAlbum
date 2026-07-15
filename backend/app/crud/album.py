"""
相册 CRUD 操作
"""
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.album import Album, AlbumPhoto
from app.models.photo import Photo


def get_album_by_id(db: Session, album_id: uuid.UUID) -> Optional[Album]:
    """根据 ID 获取相册"""
    return db.query(Album).filter(Album.id == album_id).first()


def get_user_albums(db: Session, owner_id: uuid.UUID) -> List[Album]:
    """获取用户的所有相册"""
    return db.query(Album).filter(Album.owner_id == owner_id).order_by(Album.created_at.desc()).all()


def create_album(db: Session, owner_id: uuid.UUID, name: str, description: str = None, 
                 album_type: str = "manual", conditions: dict = None) -> Album:
    """创建相册"""
    album = Album(
        owner_id=owner_id,
        name=name,
        description=description,
        album_type=album_type,
        conditions=conditions,
    )
    db.add(album)
    db.commit()
    db.refresh(album)
    return album


def update_album(db: Session, album: Album, **kwargs) -> Album:
    """更新相册"""
    for key, value in kwargs.items():
        if value is not None and hasattr(album, key):
            setattr(album, key, value)
    db.commit()
    db.refresh(album)
    return album


def delete_album(db: Session, album: Album) -> bool:
    """删除相册"""
    try:
        # 先删除相册与照片的关联关系
        db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album.id).delete()
        # 删除相册
        db.delete(album)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def add_photo_to_album(db: Session, album_id: uuid.UUID, photo_id: uuid.UUID) -> bool:
    """将照片添加到相册"""
    try:
        # 检查是否已存在
        existing = db.query(AlbumPhoto).filter(
            AlbumPhoto.album_id == album_id,
            AlbumPhoto.photo_id == photo_id
        ).first()
        if existing:
            return True
        
        album_photo = AlbumPhoto(album_id=album_id, photo_id=photo_id)
        db.add(album_photo)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def remove_photo_from_album(db: Session, album_id: uuid.UUID, photo_id: uuid.UUID) -> bool:
    """从相册中移除照片"""
    try:
        db.query(AlbumPhoto).filter(
            AlbumPhoto.album_id == album_id,
            AlbumPhoto.photo_id == photo_id
        ).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def get_album_photos(db: Session, album_id: uuid.UUID, page: int = 1, page_size: int = 50) -> tuple:
    """获取相册中的照片"""
    query = (
        db.query(Photo)
        .join(AlbumPhoto, AlbumPhoto.photo_id == Photo.id)
        .filter(AlbumPhoto.album_id == album_id)
        .order_by(Photo.photo_time.desc())
    )
    
    total = query.count()
    photos = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return total, photos


def get_album_photo_count(db: Session, album_id: uuid.UUID) -> int:
    """获取相册中的照片数量"""
    return db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).count()
