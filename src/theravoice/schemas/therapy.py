"""Therapy exercise / session schemas.

Exercises are configurable, non-prescriptive speech practice activities.
When `require_clinician_approval` is enabled, unapproved exercises must not
be presented as medical instructions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Exercise(BaseModel):
    id: str
    name: str
    description: str
    duration_seconds: int
    instructions: list[str] = Field(default_factory=list)
    clinician_approved: bool = False


class TherapySession(BaseModel):
    id: str
    patient_id: str
    exercise_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed: bool = False
    notes: str | None = None
