"""历史记录相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


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
    provider_id: int | None = Field(default=None, description="使用的模型提供商 ID")
    model: str | None = Field(default=None, description="使用的模型名称")


class HistoryItem(BaseModel):
    """单条上传历史记录。

    image_url 是图片在 S3 桶中的公开访问链接，
    前端可直接用于 ``<img src>`` 展示。
    """

    image_id: str = Field(description="图片唯一标识")
    filename: str = Field(description="上传文件名")
    image_url: str | None = Field(default=None, description="原始图片的公开访问链接")
    created_at: str = Field(description="上传时间")
    detections: list[HistoryBoxItem] = Field(description="检测框列表")
    judge: HistoryJudgeItem | None = Field(default=None, description="判定结果（未判定则为 None）")


class HistoryPage(BaseModel):
    """分页历史数据。"""

    items: list[HistoryItem] = Field(description="当前页数据")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码（从 1 开始）")
    page_size: int = Field(description="每页条数")
    total_pages: int = Field(description="总页数")
