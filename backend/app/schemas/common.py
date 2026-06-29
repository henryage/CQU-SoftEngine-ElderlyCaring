"""通用响应与分页 schema。

所有接口统一使用 `R` 包装返回，错误响应统一使用 `ErrorResponse`。
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class R(BaseModel):
    """统一响应包装。

    所有接口成功/失败都返回此结构。
    - `code=0` 表示成功，非 0 表示业务错误
    - `msg` 为给前端展示的提示信息
    - `data` 为业务数据，失败时通常为 null
    """
    code: int = Field(default=0, description="业务码：0=成功，非0=失败", examples=[0])
    msg: str = Field(default="ok", description="提示信息", examples=["ok"])
    data: Any | None = Field(default=None, description="业务数据，失败时为 null", examples=[{"user_id": 1}])

    @classmethod
    def ok(cls, data: Any = None, msg: str = "ok") -> "R":
        return cls(code=0, msg=msg, data=data)

    @classmethod
    def fail(cls, msg: str = "fail", code: int = -1, data: Any = None) -> "R":
        return cls(code=code, msg=msg, data=data)


class ErrorResponse(BaseModel):
    """FastAPI HTTP 异常响应（401/403/404/422/500 等）。

    注意：FastAPI 抛 HTTPException 时返回的是 `{"detail": "..."}` 结构，
    与业务层的 `R` 不同。前端需同时处理这两种结构。
    """
    detail: str = Field(..., description="错误描述", examples=["缺少认证令牌"])


class Page(BaseModel, Generic[T]):
    """分页响应。

    所有列表接口统一用此结构返回。
    """
    total: int = Field(..., description="总记录数", examples=[100])
    page: int = Field(..., description="当前页码（从 1 开始）", examples=[1])
    page_size: int = Field(..., description="每页条数", examples=[20])
    items: list[T] = Field(..., description="当前页数据列表")


class PageQuery(BaseModel):
    """分页查询参数（所有列表接口通用）。"""
    page: int = Field(default=1, ge=1, description="页码，从 1 开始", examples=[1])
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数，1-100", examples=[20])
