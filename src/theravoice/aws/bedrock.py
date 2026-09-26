"""Optional AWS Bedrock adapter, for future LLM-assisted summary generation.

Not wired into the default pipeline: TheraVoice's summaries are generated
deterministically (see agents/summary_agent.py) so behavior stays predictable
and auditable. This adapter is a placeholder for opt-in enhancement.
"""

from __future__ import annotations

from theravoice.aws.s3 import S3NotConfiguredError
from theravoice.config.settings import get_settings


def invoke_model(model_id: str, prompt: str) -> str:
    settings = get_settings()
    if not settings.aws.enabled:
        raise S3NotConfiguredError("AWS is disabled (aws.enabled=false in config).")
    try:
        import boto3
    except ImportError as exc:
        raise S3NotConfiguredError(
            "boto3 is not installed. Install the 'aws' extra to enable Bedrock support."
        ) from exc
    client = boto3.client("bedrock-runtime", region_name=settings.aws.region)
    response = client.invoke_model(modelId=model_id, body=prompt.encode("utf-8"))
    return response["body"].read().decode("utf-8")
