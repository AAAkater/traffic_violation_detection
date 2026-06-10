"""全局配置 — 使用 pydantic-settings 管理所有参数。

支持环境变量和 .env 文件，所有字段均可通过环境变量覆盖，
环境变量名规则：前缀 TRAFFIC_ + 大写字段名，如 TRAFFIC_MODEL_PATH。

使用方式：
    from detector.settings import settings
    print(settings.model_path)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置（检测 + 判定）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    # ── 检测模块 ──
    yolo_model_path: str = ""
    """YOLO 模型权重路径。"""

    yolo_conf_threshold: float = 0.4
    """YOLO 检测置信度阈值。"""

    yolo_device: str = "cuda"
    """推理设备：\"cuda\" 使用 GPU，\"cpu\" 使用 CPU，\"cuda:0\" 指定具体 GPU。"""

    # ── 判定模块 ──
    judge_model: str = "qwen3.7-plus"
    """判定模型名称。"""

    judge_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """判定 API 基础 URL。"""

    judge_api_key: str = ""
    """判定 API 密钥。"""


# 全局单例
settings = Settings()
