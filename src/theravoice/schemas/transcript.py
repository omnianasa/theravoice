"""Transcript segment schema."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    id: str
    patient_id: str
    text: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float | None = None
