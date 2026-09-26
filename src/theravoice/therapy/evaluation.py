"""Placeholder evaluation hooks for therapy sessions.

Evaluation here is intentionally descriptive (did the session happen, roughly
how long) rather than any kind of automated clinical scoring.
"""

from __future__ import annotations

from theravoice.schemas.therapy import TherapySession


def summarize_session(session: TherapySession) -> dict:
    return {
        "session_id": session.id,
        "patient_id": session.patient_id,
        "exercise_id": session.exercise_id,
        "completed": session.completed,
        "notes": session.notes,
    }
