"""Generates reminder Action objects for upcoming/near-due medication."""

from __future__ import annotations

from theravoice.schemas.action import Action
from theravoice.schemas.medication import Medication, MedicationSchedule


def build_reminder(patient_id: str, medication: Medication, schedule: MedicationSchedule) -> Action:
    return Action(
        patient_id=patient_id,
        type="REMIND",
        message=f"Reminder: {medication.name} is scheduled around {schedule.scheduled_time}.",
        priority="normal",
        requires_confirmation=False,
        metadata={"medication_id": medication.id, "scheduled_time": schedule.scheduled_time},
    )
