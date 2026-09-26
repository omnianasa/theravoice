"""Event schema.

Events describe OBSERVED DEVIATIONS from a patient's own historical baseline.
They are never medical diagnoses. See docs/limitations.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from theravoice.schemas.evidence import Evidence

Severity = Literal["normal", "warning", "significant", "insufficient_data"]


class Event(BaseModel):
    type: str
    patient_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: Severity
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
