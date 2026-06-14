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

    # ── 运行模式 ──
    SYSTEM_DEV: bool = False
    """开发模式：为 True 时日志输出 DEBUG 级别到控制台。"""
    SYSTEM_PORT: int = 8010
    """系统运行端口。"""

    # ── 检测模块 ──
    YOLO_MODEL_PATH: str = ""
    """YOLO 模型权重路径。"""

    YOLO_CONF_THRESHOLD: float = 0.4
    """YOLO 检测置信度阈值。"""

    YOLO_DEVICE: str = "cuda"
    """推理设备：\"cuda\" 使用 GPU，\"cpu\" 使用 CPU，\"cuda:0\" 指定具体 GPU。"""

    # ── 默认系统提示词 ──
    default_system_prompt: str = ""
    """默认系统提示词，为空时使用 VisionClient 内置提示词。"""

    # ── 数据库 ──
    DB_SERVER: str = "localhost"
    """数据库主机地址。"""

    DB_PORT: int = 5432
    """数据库端口。"""

    DB_USER: str = "tvd"
    """数据库用户名。"""

    DB_PASSWORD: str = "tvd123"
    """数据库密码。"""

    DB_NAME: str = "tvd"
    """数据库名称。"""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """自动拼接的数据库连接 URL。"""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_SERVER,
            port=self.DB_PORT,
            path=self.DB_NAME,
        )

    # ── 对象存储 (S3 兼容) ──
    S3_SERVER: str = "localhost"
    """S3 兼容服务主机地址。"""

    S3_PORT: int = 9000
    """S3 兼容服务端口。"""

    S3_ACCESS_KEY: str = "tvd"
    """S3 访问密钥。"""

    S3_SECRET_KEY: str = "tvd123"
    """S3 密钥。"""

    S3_BUCKET_NAME: str = "tvd"
    """S3 存储桶名称。"""

    @computed_field
    @property
    def S3_ENDPOINT(self) -> str:
        """自动拼接的 S3 兼容端点 URL。"""
        return f"http://{self.S3_SERVER}:{self.S3_PORT}"


# 全局单例
settings = Settings()
