"""Optional AWS SNS-backed notification channel."""

from __future__ import annotations

from theravoice.aws.s3 import S3NotConfiguredError
from theravoice.config.settings import get_settings
from theravoice.notifications.channels import NotificationChannel


class SNSChannel(NotificationChannel):
    def __init__(self, topic_arn: str) -> None:
        self._topic_arn = topic_arn

    def send(self, patient_id: str, message: str) -> None:
        settings = get_settings()
        if not settings.aws.enabled:
            raise S3NotConfiguredError("AWS is disabled (aws.enabled=false in config).")
        try:
            import boto3
        except ImportError as exc:
            raise S3NotConfiguredError(
                "boto3 is not installed. Install the 'aws' extra to enable SNS support."
            ) from exc
        client = boto3.client("sns", region_name=settings.aws.region)
        client.publish(TopicArn=self._topic_arn, Message=f"[{patient_id}] {message}")
