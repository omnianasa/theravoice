"""Optional S3 adapter. Only used if aws.enabled=true in config; requires boto3."""

from __future__ import annotations

from theravoice.config.settings import get_settings


class S3NotConfiguredError(RuntimeError):
    pass


def _get_client():
    settings = get_settings()
    if not settings.aws.enabled:
        raise S3NotConfiguredError("AWS is disabled (aws.enabled=false in config).")
    try:
        import boto3
    except ImportError as exc:
        raise S3NotConfiguredError(
            "boto3 is not installed. Install the 'aws' extra to enable S3 support."
        ) from exc
    return boto3.client("s3", region_name=settings.aws.region)


def upload_bytes(key: str, data: bytes) -> None:
    settings = get_settings()
    if not settings.aws.s3_bucket:
        raise S3NotConfiguredError("aws.s3_bucket is not set in config.")
    client = _get_client()
    client.put_object(Bucket=settings.aws.s3_bucket, Key=key, Body=data)


def download_bytes(key: str) -> bytes:
    settings = get_settings()
    if not settings.aws.s3_bucket:
        raise S3NotConfiguredError("aws.s3_bucket is not set in config.")
    client = _get_client()
    response = client.get_object(Bucket=settings.aws.s3_bucket, Key=key)
    return response["Body"].read()
