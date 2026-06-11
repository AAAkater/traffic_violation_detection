"""统一响应模型 — 所有 API 接口返回此结构。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Response[T](BaseModel):
    """统一响应结构。

    code=0 表示成功，非 0 表示错误。
    """

    code: int = Field(default=0, description="状态码，0 成功，非 0 错误")
    msg: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="返回数据")


class DetectionItem(BaseModel):
    """单个检测框结果。"""

    quadrant: str = Field(
        description="所属象限: top_left(左上-红灯区) / top_right(右上-绿灯区) / bottom_left(左下-黄灯区)"
    )
    bbox: list[float] = Field(
        description="[x1, y1, x2, y2] 边界框坐标（原始图片坐标系）"
    )
    confidence: float = Field(description="检测置信度")
    class_name: str = Field(description="类别名称，如 red/green/yellow/off/wait_on")


class DetectData(BaseModel):
    """检测接口返回数据。"""

    image_id: str = Field(description="图片唯一标识，同一次检测的所有框共享此 ID")
    detections: list[DetectionItem] = Field(description="所有检测框列表")


class JudgeData(BaseModel):
    """违法判定结果数据。"""

    image_id: str = Field(description="关联的检测图片唯一标识")
    violated: bool = Field(description="是否闯红灯")
    reason: str = Field(default="", description="判定理由")


class HistoryBoxItem(BaseModel):
    """历史记录中的单个检测框。"""

    quadrant: str = Field(description="所属象限")
    bbox: list[float] = Field(description="[x1, y1, x2, y2] 边界框坐标")
    confidence: float = Field(description="检测置信度")
    class_name: str = Field(description="类别名称")


class HistoryJudgeItem(BaseModel):
    """历史记录中的判定结果。"""

    violated: bool = Field(description="是否闯红灯")
    reason: str = Field(default="", description="判定理由")
    prompt_name: str | None = Field(default=None, description="使用的系统提示词名称")


class HistoryItem(BaseModel):
    """单条上传历史记录。"""

    image_id: str = Field(description="图片唯一标识")
    filename: str = Field(description="上传文件名")
    image_url: str | None = Field(default=None, description="原始图片 URL")
    created_at: str = Field(description="上传时间")
    detections: list[HistoryBoxItem] = Field(description="检测框列表")
    judge: HistoryJudgeItem | None = Field(
        default=None, description="判定结果（未判定则为 None）"
    )


class HistoryPage(BaseModel):
    """分页历史数据。"""

    items: list[HistoryItem] = Field(description="当前页数据")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码（从 1 开始）")
    page_size: int = Field(description="每页条数")
    total_pages: int = Field(description="总页数")
