"""对象存储模块 — 使用 S3 兼容协议上传文件到 RustFS/MinIO。"""

from __future__ import annotations

import io
import uuid
from datetime import datetime

from boto3.session import Config as BotoConfig
from botocore.exceptions import ClientError

from detector.settings import settings
from detector.utils import logger


def _get_s3_client():
    """创建 S3 兼容客户端连接到 RustFS。"""
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.rustfs_endpoint,
        aws_access_key_id=settings.rustfs_access_key,
        aws_secret_access_key=settings.rustfs_secret_key,
        config=BotoConfig(
            signature_version="s3v4",
            region_name=settings.rustfs_region,
        ),
    )


def _ensure_bucket(client, bucket: str) -> None:
    """确保存储桶存在，不存在则创建。"""
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        logger.info(f"[storage] 创建存储桶: {bucket}")
        client.create_bucket(Bucket=bucket)


def upload_bytes(
    data: bytes,
    filename: str | None = None,
    content_type: str = "image/jpeg",
    bucket: str | None = None,
    prefix: str = "traffic",
) -> str:
    """上传二进制数据到 RustFS，返回可访问的 URL。

    Args:
        data: 图片二进制数据。
        filename: 原始文件名（用于扩展名推断）。
        content_type: MIME 类型。
        bucket: 存储桶名称，默认使用 settings.rustfs_bucket。
        prefix: 对象键前缀（按日期组织）。

    Returns:
        上传后的完整 URL。
    """
    bucket = bucket or settings.rustfs_bucket
    client = _get_s3_client()
    _ensure_bucket(client, bucket)

    # 生成对象键: prefix/YYYY-MM-DD/uuid.ext
    ext = "jpg"
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        # 常见图片扩展名映射
        if ext in ("jpeg",):
            ext = "jpg"

    date_str = datetime.now().strftime("%Y-%m-%d")
    object_key = f"{prefix}/{date_str}/{uuid.uuid4().hex[:16]}.{ext}"

    client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )

    url = f"{settings.rustfs_endpoint}/{bucket}/{object_key}"
    logger.debug(f"[storage] 上传成功: {url}")
    return url


def download_image(image_url: str) -> bytes:
    """从 RustFS 下载图片，返回二进制数据。

    Args:
        image_url: RustFS 中图片的完整 URL。

    Returns:
        图片的二进制数据。
    """
    client = _get_s3_client()
    bucket = settings.rustfs_bucket

    # 从 URL 中提取 object_key: endpoint/bucket/key → key
    prefix = f"{settings.rustfs_endpoint}/{bucket}/"
    if not image_url.startswith(prefix):
        raise ValueError(f"image_url 不属于当前 RustFS bucket: {image_url}")
    object_key = image_url[len(prefix) :]

    response = client.get_object(Bucket=bucket, Key=object_key)
    data = response["Body"].read()
    logger.debug(f"[storage] 下载成功: {object_key}, 大小: {len(data)} bytes")
    return data


def upload_pil_image(
    img,
    filename: str | None = None,
    content_type: str = "image/jpeg",
    bucket: str | None = None,
    prefix: str = "traffic",
    format: str = "JPEG",
    quality: int = 95,
) -> str:
    """上传 PIL Image 到 RustFS，返回可访问的 URL。

    Args:
        img: PIL Image 对象。
        filename: 原始文件名。
        content_type: MIME 类型。
        bucket: 存储桶名称。
        prefix: 对象键前缀。
        format: PIL 保存格式（JPEG/PNG）。
        quality: JPEG 质量。

    Returns:
        上传后的完整 URL。
    """
    buf = io.BytesIO()
    img.save(buf, format=format, quality=quality)
    return upload_bytes(
        buf.getvalue(),
        filename=filename,
        content_type=content_type,
        bucket=bucket,
        prefix=prefix,
    )
