"""Audio segment schema."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AudioSegment(BaseModel):
    id: str
    patient_id: str
    path: str | None = None
    sample_rate: int
    duration_seconds: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "unknown"
