"""
Pydantic 数据模型（Request / Response Schema）
"""
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, UserUpdate, TokenResponse,
)
from app.schemas.photo import (
    PhotoDetailResponse, PhotoListItem, PhotoMetadataResponse,
    PhotoDescriptionResponse, FaceBoxResponse,
    PhotoUpdateRequest, ReanalyzeRequest, BatchPhotoRequest,
    BatchUploadResponse, UploadResult, TimelineGroup, MapPhotoItem,
)
from app.schemas.task import TaskResponse, TaskStatsResponse
from app.schemas.response import BaseResponse, PaginatedData
from app.schemas.album import AlbumCreate, AlbumResponse, AlbumUpdate
from app.schemas.face import FaceIdentityResponse, FaceResponse
from app.schemas.agent import (
    AgentSessionCreate, AgentSessionResponse, AgentMessageResponse, ChatRequest,
)
