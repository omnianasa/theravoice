"""Biomarker value / snapshot schemas."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BiomarkerValue(BaseModel):
    name: str
    value: float | None
    unit: str | None = None
    confidence: float | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "unknown"
    available: bool = True
    reason_unavailable: str | None = None


class BiomarkerSnapshot(BaseModel):
    patient_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    values: list[BiomarkerValue] = Field(default_factory=list)

    def as_dict(self) -> dict[str, float]:
        """Return {name: value} for available, numeric values only."""
        return {v.name: v.value for v in self.values if v.available and v.value is not None}
