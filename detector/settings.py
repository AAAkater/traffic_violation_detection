"""全局配置 — 使用 pydantic-settings 管理所有参数。

支持环境变量和 .env 文件，所有字段均可通过环境变量覆盖，
环境变量名规则：前缀 TRAFFIC_ + 大写字段名，如 TRAFFIC_DATASET_DIR。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DetectionSettings(BaseSettings):
    """检测模块配置。"""

    model_path: str = "/home/mopo3/code/models/Ultralytics/YOLO26/yolo26x.pt"
    """YOLO 模型权重路径。"""

    conf_threshold: float = 0.4
    """YOLO 检测置信度阈值。"""

    upper_ratio: float = 0.5
    """裁剪上半区域比例。"""

    edge_ratio: float = 0.20
    """左右边缘裁剪比例。"""

    model_config = SettingsConfigDict(
        env_prefix="TRAFFIC_DET_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class JudgeSettings(BaseSettings):
    """判定模块配置。"""

    enabled: bool = True
    """是否启用判定步骤。"""

    model: str = "qwen3.6-plus"
    """判定模型名称。"""

    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """判定 API 基础 URL。"""

    api_key: str = ""
    """判定 API 密钥。"""

    max_tokens: int = 20000
    """最大生成 token 数。"""

    temperature: float = 0.0
    """生成温度。"""

    concurrency: int = 5
    """判定并发数。"""

    model_config = SettingsConfigDict(
        env_prefix="TRAFFIC_JUDGE_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class PipelineSettings(BaseSettings):
    """整合流水线配置（检测 + 判定）。"""

    # dataset_dir: str = "/home/mopo3/code/datasets/违法"
    dataset_dir: str = "/home/mopo3/code/python/traffic_violation_detection/data"

    """图片文件夹路径。"""

    output_dir: str | None = None
    """输出根目录。为 None 时自动生成带时间戳的路径。"""

    detection: DetectionSettings = DetectionSettings()
    """检测模块配置。"""

    judge: JudgeSettings = JudgeSettings()
    """判定模块配置。"""

    model_config = SettingsConfigDict(
        env_prefix="TRAFFIC_",
        env_file=".env",
        env_file_encoding="utf-8",
    )
