"""
数据库 ORM 模型
将所有模型导入到此文件，确保 Alembic 和 SQLAlchemy 能发现所有模型
"""
from app.models.user import User
from app.models.photo import Photo, PhotoMetadata
from app.models.face import Face, FaceIdentity
from app.models.description import ImageDescription, PhotoTag, PhotoTagRelation
from app.models.album import Album, AlbumPhoto
from app.models.agent import AgentSession, AgentMessage
