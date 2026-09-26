"""Builds a DailySummary report from persisted events/actions for a given day."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from theravoice.schemas.report import DailySummary
from theravoice.storage.repositories.event import EventRepository


def build_daily_summary(session: Session, patient_id: str, day: date) -> DailySummary:
    event_repo = EventRepository(session)
    events = event_repo.list_for_patient(patient_id, limit=500)

    day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    day_events = [e for e in events if day_start <= e.timestamp <= day_end]

    observations: list[str] = []
    context_notes: list[str] = []
    for event in day_events:
        for ev in event.evidence:
            if ev.type == "contextual_observation":
                context_notes.append(ev.description)
            else:
                observations.append(ev.description)

    return DailySummary(
        patient_id=patient_id,
        day=day,
        observations=observations,
        context_notes=context_notes,
        suggested_actions=[],
    )
