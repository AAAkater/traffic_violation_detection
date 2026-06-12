"""违法判定相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class ViolationResult(BaseModel):
    """交通违法判定结果。"""

    violated: bool = Field(description="是否违反交通灯（闯红灯）")
    reason: str = Field(description="判定理由")
    raw_response: str = Field(default="", description="模型原始流式回复全文")


class JudgeData(BaseModel):
    """违法判定结果数据。"""

    image_id: str = Field(description="关联的检测图片唯一标识")
    violated: bool = Field(description="是否闯红灯")
    reason: str = Field(default="", description="判定理由")
    provider_id: int = Field(description="使用的模型提供商 ID")
    model: str = Field(description="使用的模型名称")
