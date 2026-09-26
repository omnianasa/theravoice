"""Medication event construction helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from theravoice.schemas.medication import MedicationEvent


def log_medication_event(patient_id: str, medication_id: str, status: str) -> MedicationEvent:
    return MedicationEvent(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        medication_id=medication_id,
        taken_at=datetime.now(timezone.utc).isoformat(),
        status=status,
    )
