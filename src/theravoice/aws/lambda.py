"""Optional AWS Lambda invocation adapter (e.g. to trigger async processing)."""

from __future__ import annotations

import json

from theravoice.aws.s3 import S3NotConfiguredError
from theravoice.config.settings import get_settings


def invoke_function(function_name: str, payload: dict) -> dict:
    settings = get_settings()
    if not settings.aws.enabled:
        raise S3NotConfiguredError("AWS is disabled (aws.enabled=false in config).")
    try:
        import boto3
    except ImportError as exc:
        raise S3NotConfiguredError(
            "boto3 is not installed. Install the 'aws' extra to enable Lambda support."
        ) from exc
    client = boto3.client("lambda", region_name=settings.aws.region)
    response = client.invoke(FunctionName=function_name, Payload=json.dumps(payload).encode("utf-8"))
    return json.loads(response["Payload"].read())
