"""系统提示词相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class PromptData(BaseModel):
    """系统提示词数据。"""

    name: str = Field(description="提示词名称")
    content: str = Field(description="提示词内容")


class PromptCreate(BaseModel):
    """创建系统提示词请求体。"""

    name: str = Field(min_length=1, max_length=100, description="提示词名称")
    content: str = Field(min_length=1, description="提示词内容")


class PromptListItem(BaseModel):
    """系统提示词列表项。"""

    name: str = Field(description="提示词名称")
    content: str = Field(description="提示词内容")
    is_active: bool = Field(description="是否激活")
    updated_at: str = Field(description="更新时间")
