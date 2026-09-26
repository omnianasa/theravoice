"""Minimal audit logging for sensitive operations.

Never logs passwords, secrets, raw audio, or full transcript content --
only operation metadata.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

audit_logger = logging.getLogger("theravoice.audit")


def log_sensitive_operation(operation: str, patient_id: str, actor: str = "system") -> None:
    audit_logger.info(
        "audit_event",
        extra={
            "operation": operation,
            "patient_id": patient_id,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
