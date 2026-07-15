"""
统一响应模型

所有 API 接口均使用 BaseResponse 包装返回值，
确保前端可以用统一的方式处理成功和失败响应。

使用方式:
    # 成功
    return BaseResponse(data=some_object)

    # 业务失败（不抛异常）
    return BaseResponse(code=404, msg="照片不存在", data=None)

    # 仅框架级未预期异常才 raise HTTPException（由全局异常处理器捕获）
"""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """统一响应模型：code + msg + data"""

    code: int = Field(default=200, description="状态码：200=成功，4xx=客户端错误，5xx=服务端错误")
    msg: str = Field(default="操作成功", description="提示信息")
    data: Optional[T] = Field(default=None, description="业务数据（成功时返回，失败时为 null）")

    model_config = {"from_attributes": True}


class PaginatedData(BaseModel):
    """分页数据结构，配合 BaseResponse[PaginatedData] 使用"""
    total: int
    page: int
    page_size: int
    items: list
