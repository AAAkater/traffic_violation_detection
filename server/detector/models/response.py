"""统一响应模型 — 所有 API 接口返回此结构。"""

from pydantic import BaseModel, Field


class Response[T](BaseModel):
    """统一响应结构。

    code=0 表示成功，非 0 表示错误。
    """

    code: int = Field(default=0, description="状态码，0 成功，非 0 错误")
    msg: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="返回数据")
