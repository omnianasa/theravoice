"""Builds a clinician-oriented, longitudinal, non-diagnostic summary."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from theravoice.schemas.report import ClinicalSummary
from theravoice.storage.repositories.event import EventRepository


def build_clinical_summary(
    session: Session,
    patient_id: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> ClinicalSummary:
    event_repo = EventRepository(session)
    events = event_repo.list_for_patient(patient_id, limit=1000)

    period_end = period_end or datetime.now(timezone.utc)
    period_start = period_start or events[-1].timestamp if events else period_end

    in_range = [e for e in events if period_start <= e.timestamp <= period_end]
    baseline_status = "ok" if in_range else "insufficient_data"

    notes = [
        f"{len(in_range)} descriptive deviation event(s) were recorded in this period.",
    ]

    return ClinicalSummary(
        patient_id=patient_id,
        period_start=period_start,
        period_end=period_end,
        total_observations=len(in_range),
        events=in_range,
        baseline_status=baseline_status,
        notes=notes,
    )
