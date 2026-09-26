"""Optional DynamoDB adapter. Only used if aws.enabled=true; requires boto3."""

from __future__ import annotations

from theravoice.aws.s3 import S3NotConfiguredError
from theravoice.config.settings import get_settings


def _get_table():
    settings = get_settings()
    if not settings.aws.enabled:
        raise S3NotConfiguredError("AWS is disabled (aws.enabled=false in config).")
    if not settings.aws.dynamodb_table:
        raise S3NotConfiguredError("aws.dynamodb_table is not set in config.")
    try:
        import boto3
    except ImportError as exc:
        raise S3NotConfiguredError(
            "boto3 is not installed. Install the 'aws' extra to enable DynamoDB support."
        ) from exc
    resource = boto3.resource("dynamodb", region_name=settings.aws.region)
    return resource.Table(settings.aws.dynamodb_table)


def put_item(item: dict) -> None:
    table = _get_table()
    table.put_item(Item=item)


def get_item(key: dict) -> dict | None:
    table = _get_table()
    response = table.get_item(Key=key)
    return response.get("Item")
