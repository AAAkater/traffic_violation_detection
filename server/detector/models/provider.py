"""模型提供商相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class ProviderData(BaseModel):
    """模型提供商配置数据。"""

    id: int = Field(description="提供商 ID")
    name: str = Field(description="提供商名称")
    base_url: str = Field(description="API 基础 URL")
    api_key: str = Field(description="API 密钥（脱敏）")
    activated_models: list[str] = Field(default_factory=list, description="已激活的模型名称列表")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


class ProviderCreate(BaseModel):
    """创建模型提供商请求体。"""

    name: str = Field(min_length=1, max_length=100, description="提供商名称")
    base_url: str = Field(min_length=1, max_length=500, description="API 基础 URL")
    api_key: str = Field(min_length=1, max_length=500, description="API 密钥")


class ProviderUpdate(BaseModel):
    """更新模型提供商请求体。"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="提供商名称")
    base_url: str | None = Field(default=None, min_length=1, max_length=500, description="API 基础 URL")
    api_key: str | None = Field(default=None, min_length=1, max_length=500, description="API 密钥")


class ModelInfo(BaseModel):
    """单个模型信息。"""

    id: str = Field(description="模型 ID，如 qwen3.7-plus")
    owned_by: str = Field(default="", description="模型所有者")
    created: int | None = Field(default=None, description="创建时间戳")


class ProviderModelsData(BaseModel):
    """提供商的模型列表数据。"""

    provider_id: int = Field(description="提供商 ID")
    provider_name: str = Field(description="提供商名称")
    models: list[ModelInfo] = Field(description="可用模型列表")


class ModelActivateRequest(BaseModel):
    """激活模型请求体。"""

    model: str = Field(min_length=1, max_length=200, description="要激活的模型名称")


class ModelDeactivateRequest(BaseModel):
    """停用模型请求体。"""

    model: str = Field(min_length=1, max_length=200, description="要停用的模型名称")
