"""Evidence schema: a single piece of descriptive support for an event."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    type: str
    source: str
    description: str
    value: float | str | None = None
    confidence: float | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
