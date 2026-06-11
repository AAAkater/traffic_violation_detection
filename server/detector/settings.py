"""全局配置 — 使用 pydantic-settings 管理所有参数。

支持环境变量和 .env 文件，所有字段均可通过环境变量覆盖，
环境变量名即字段名大写，如 POSTGRES_SERVER。

使用方式：
    from detector.settings import settings
    print(settings.model_path)
"""

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置（检测 + 判定）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
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

    # ── 默认系统提示词 ──
    default_system_prompt: str = ""
    """默认系统提示词，为空时使用 VisionClient 内置提示词。"""

    # ── 数据库 ──
    POSTGRES_SERVER: str = "localhost"
    """数据库主机地址。"""

    POSTGRES_PORT: int = 5432
    """数据库端口。"""

    POSTGRES_USER: str = "ai"
    """数据库用户名。"""

    POSTGRES_PASSWORD: str = "ai123"
    """数据库密码。"""

    POSTGRES_DB: str = "dev"
    """数据库名称。"""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """自动拼接的数据库连接 URL。"""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # ── 对象存储 (S3 兼容) ──
    s3_server: str = "localhost"
    """S3 兼容服务主机地址。"""

    s3_port: int = 9000
    """S3 兼容服务端口。"""

    s3_access_key: str = "minioadmin"
    """S3 访问密钥。"""

    s3_secret_key: str = "minioadmin"
    """S3 密钥。"""

    s3_bucket: str = "traffic"
    """S3 存储桶名称。"""

    @computed_field
    @property
    def s3_endpoint(self) -> str:
        """自动拼接的 S3 兼容端点 URL。"""
        return f"http://{self.s3_server}:{self.s3_port}"


# 全局单例
settings = Settings()
