"""Medication and medication-schedule schemas.

TheraVoice never changes medication and never claims medication has "worn
off". These schemas only describe human-entered facts about prescriptions
and scheduled times, used purely for contextual annotation.
"""

from __future__ import annotations

from pydantic import BaseModel


class Medication(BaseModel):
    id: str
    patient_id: str
    name: str
    dosage: float | None = None
    unit: str | None = None
    active: bool = True


class MedicationSchedule(BaseModel):
    medication_id: str
    scheduled_time: str  # "HH:MM", local to the patient's timezone
    timezone: str = "UTC"
    days_of_week: list[int] = []  # 0=Monday ... 6=Sunday; empty = every day


class MedicationEvent(BaseModel):
    id: str
    patient_id: str
    medication_id: str
    taken_at: str | None = None  # ISO timestamp, human-logged
    status: str = "unknown"  # e.g. "taken", "skipped", "unknown"
