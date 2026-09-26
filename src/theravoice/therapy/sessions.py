"""Therapy session lifecycle helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from theravoice.schemas.therapy import TherapySession


def start_session(patient_id: str, exercise_id: str) -> TherapySession:
    return TherapySession(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        exercise_id=exercise_id,
        started_at=datetime.now(timezone.utc),
        completed=False,
    )


def complete_session(session: TherapySession, notes: str | None = None) -> TherapySession:
    session.completed = True
    session.notes = notes
    return session
