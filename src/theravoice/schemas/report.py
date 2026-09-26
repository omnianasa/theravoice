"""Report schemas for daily / timeline / clinical summaries."""

from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import BaseModel, Field

from theravoice.schemas.action import Action
from theravoice.schemas.event import Event


class DailySummary(BaseModel):
    patient_id: str
    day: date
    observations: list[str] = Field(default_factory=list)
    context_notes: list[str] = Field(default_factory=list)
    suggested_actions: list[Action] = Field(default_factory=list)
    disclaimer: str = (
        "These observations are descriptive and are not a diagnosis. "
        "Please consult a qualified clinician for medical concerns."
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TimelineEntry(BaseModel):
    timestamp: datetime
    kind: str  # "event" | "action" | "observation"
    summary: str
    details: dict = Field(default_factory=dict)


class Timeline(BaseModel):
    patient_id: str
    entries: list[TimelineEntry] = Field(default_factory=list)


class ClinicalSummary(BaseModel):
    patient_id: str
    period_start: datetime
    period_end: datetime
    total_observations: int
    events: list[Event] = Field(default_factory=list)
    baseline_status: str
    notes: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This report is a descriptive, longitudinal aid intended to support "
        "clinical judgement. It is not a diagnosis and should not be used as "
        "the sole basis for clinical decisions."
    )
