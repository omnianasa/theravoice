"""Builds a chronological Timeline of events/actions for a patient."""

from __future__ import annotations

from sqlalchemy.orm import Session

from theravoice.schemas.report import Timeline, TimelineEntry
from theravoice.storage.repositories.event import EventRepository


def build_timeline(session: Session, patient_id: str, limit: int = 200) -> Timeline:
    event_repo = EventRepository(session)
    events = event_repo.list_for_patient(patient_id, limit=limit)

    entries = [
        TimelineEntry(
            timestamp=event.timestamp,
            kind="event",
            summary=f"{event.type} ({event.severity})",
            details={"metadata": event.metadata, "evidence_count": len(event.evidence)},
        )
        for event in events
    ]
    entries.sort(key=lambda e: e.timestamp)
    return Timeline(patient_id=patient_id, entries=entries)
