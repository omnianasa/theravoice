"""Medication schedule helpers (human-entered facts only)."""

from __future__ import annotations

from theravoice.schemas.medication import MedicationSchedule


def is_scheduled_today(schedule: MedicationSchedule, weekday: int) -> bool:
    if not schedule.days_of_week:
        return True
    return weekday in schedule.days_of_week
