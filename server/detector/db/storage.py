"""对象存储模块 — 使用 S3 兼容协议上传文件到对象存储。

提供 ``S3Storage`` 类封装所有 S3 操作，模块级 ``s3_storage`` 实例
使用全局配置初始化，供各模块直接调用。
"""

import io
import uuid
from datetime import datetime

import boto3
from boto3.session import Config as BotoConfig

from detector.settings import settings
from detector.utils import logger


class S3Storage:
    """S3 兼容对象存储客户端。

    封装 S3 连接配置和所有上传/下载操作，
    避免每次调用都重新创建客户端。

    Args:
        endpoint: S3 兼容端点 URL，如 ``http://localhost:9000``。
        access_key: S3 访问密钥。
        secret_key: S3 密钥。
        bucket: 默认存储桶名称。
    """

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
    ) -> None:
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
        )

    def ensure_bucket(self, bucket: str | None = None) -> None:
        """确保存储桶存在，不存在则创建。"""
        bucket = bucket or self.bucket_name
        try:
            self._client.create_bucket(Bucket=bucket)
            logger.info(f"[storage] 创建存储桶: {bucket}")
        except self._client.exceptions.BucketAlreadyOwnedByYou:
            logger.debug(f"[storage] 存储桶已存在: {bucket}")

    def upload_bytes(
        self,
        data: bytes,
        filename: str | None = None,
        content_type: str = "image/jpeg",
        bucket: str | None = None,
        prefix: str = "traffic",
    ) -> str:
        """上传二进制数据到对象存储，返回 object_key。

        object_key 格式: {prefix}/{YYYY-MM-DD}/{uuid}.{ext}
        """
        bucket = bucket or self.bucket_name
        ext = "jpg"
        if filename and "." in filename:
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext in ("jpeg",):
                ext = "jpg"

        date_str = datetime.now().strftime("%Y-%m-%d")
        object_key = f"{prefix}/{date_str}/{uuid.uuid4().hex[:16]}.{ext}"

        self._client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )

        logger.debug(f"[storage] 上传成功: {object_key}")
        return object_key

    def download_image(self, object_key: str, bucket: str | None = None) -> bytes:
        """从对象存储下载图片，返回二进制数据。

        Args:
            object_key: 上传时返回的文件路径 (key)。
            bucket: 存储桶名称，默认使用初始化时的 bucket。
        """
        bucket = bucket or self.bucket_name
        response = self._client.get_object(Bucket=bucket, Key=object_key)
        data = response["Body"].read()
        logger.debug(f"[storage] 下载成功: {object_key}, 大小: {len(data)} bytes")
        return data

    def public_url(self, object_key: str, bucket: str | None = None) -> str:
        """生成浏览器可访问的 presigned GET URL。

        有 S3_PUBLIC_ENDPOINT 时用公网地址签名（nginx 反代域名），
        否则用内网地址签名（开发环境直接访问）。
        """
        bucket = bucket or self.bucket_name
        public = settings.S3_PUBLIC_ENDPOINT
        if public:
            client = boto3.client(
                "s3",
                endpoint_url=public,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                config=BotoConfig(signature_version="s3v4"),
            )
        else:
            client = self._client

        return client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=settings.S3_PRESIGNED_EXPIRES,
        )

    def upload_pil_image(
        self,
        img,
        filename: str | None = None,
        content_type: str = "image/jpeg",
        bucket: str | None = None,
        prefix: str = "traffic",
        format: str = "JPEG",
        quality: int = 95,
    ) -> str:
        """上传 PIL Image 到对象存储，返回可访问的 URL。

        Args:
            img: PIL Image 对象。
            filename: 原始文件名。
            content_type: MIME 类型。
            bucket: 存储储桶名称。
            prefix: 对象键前缀。
            format: PIL 保存格式（JPEG/PNG）。
            quality: JPEG 质量。

        Returns:
            上传后的完整 URL。
        """
        buf = io.BytesIO()
        img.save(buf, format=format, quality=quality)
        return self.upload_bytes(
            buf.getvalue(),
            filename=filename,
            content_type=content_type,
            bucket=bucket,
            prefix=prefix,
        )


# ── 全局存储实例（由 lifespan 在启动时初始化） ────────────────
s3_storage: S3Storage = S3Storage(
    endpoint=settings.S3_ENDPOINT,
    access_key=settings.S3_ACCESS_KEY,
    secret_key=settings.S3_SECRET_KEY,
    bucket_name=settings.S3_BUCKET_NAME,
)
