"""ORM 模型 — 数据库表定义。"""

from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from detector.db.engine import Base


class SystemPrompt(Base):
    """系统提示词表 — 存储自定义 LLM 系统提示词。"""

    __tablename__ = "system_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="提示词名称")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="提示词内容")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为当前激活的提示词")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )


class DetectImage(Base):
    """检测原图表 — 存储每次检测上传的原始图片信息。"""

    __tablename__ = "detect_images"

    image_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="图片唯一标识")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="上传文件名")
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="原始图片在对象存储中的 URL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")


class DetectionBox(Base):
    """检测框表 — 存储每个检测框的坐标和类别。"""

    __tablename__ = "detection_boxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="关联的图片唯一标识")
    quadrant: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="象限名称: top_left / top_right / bottom_left",
    )
    bbox: Mapped[list[float]] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=False,
        comment="边界框 [x1, y1, x2, y2]",
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, comment="检测置信度")
    class_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="类别名称")


class ModelProvider(Base):
    """模型提供商表 — 存储 LLM 判定模型的连接配置。

    用户通过接口管理提供商配置，替代环境变量方式。
    每个 Provider 可提供多个模型，通过 OpenAI SDK 的 list models 接口获取。
    """

    __tablename__ = "model_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="提供商名称")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="API 基础 URL")
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="API 密钥")
    activated_models: Mapped[list[str] | None] = mapped_column(
        ARRAY(String, dimensions=1), nullable=True, comment="已激活的模型名称列表"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )


class JudgeRecord(Base):
    """判定记录表 — 存储每次 LLM 判定的结果。"""

    __tablename__ = "judge_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="关联的检测图片唯一标识")
    violated: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否闯红灯")
    reason: Mapped[str] = mapped_column(Text, default="", comment="判定理由")
    prompt_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="使用的系统提示词名称")
    provider_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="使用的模型提供商 ID")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="使用的模型名称")
