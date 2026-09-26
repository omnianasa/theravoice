"""Event repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from theravoice.schemas.event import Event
from theravoice.storage.models import EventModel


class EventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, event: Event) -> None:
        model = EventModel(
            patient_id=event.patient_id,
            type=event.type,
            severity=event.severity,
            evidence=[e.model_dump(mode="json") for e in event.evidence],
            event_metadata=event.metadata,
            timestamp=event.timestamp,
        )
        self._session.add(model)
        self._session.flush()

    def list_for_patient(self, patient_id: str, limit: int = 100) -> list[Event]:
        stmt = (
            select(EventModel)
            .where(EventModel.patient_id == patient_id)
            .order_by(EventModel.timestamp.desc())
            .limit(limit)
        )
        models = self._session.execute(stmt).scalars().all()
        from theravoice.schemas.evidence import Evidence

        return [
            Event(
                type=m.type,
                patient_id=m.patient_id,
                timestamp=m.timestamp,
                severity=m.severity,
                evidence=[Evidence.model_validate(e) for e in (m.evidence or [])],
                metadata=m.event_metadata or {},
            )
            for m in models
        ]
