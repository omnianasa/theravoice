"""Therapy repository: exercises + sessions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from theravoice.schemas.therapy import Exercise, TherapySession
from theravoice.storage.models import TherapyExerciseModel, TherapySessionModel


class TherapyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_exercise(self, exercise: Exercise) -> Exercise:
        model = TherapyExerciseModel(
            id=exercise.id,
            name=exercise.name,
            description=exercise.description,
            duration_seconds=exercise.duration_seconds,
            instructions=exercise.instructions,
            clinician_approved=exercise.clinician_approved,
        )
        self._session.merge(model)
        self._session.flush()
        return exercise

    def list_exercises(self) -> list[Exercise]:
        models = self._session.execute(select(TherapyExerciseModel)).scalars().all()
        return [
            Exercise(
                id=m.id,
                name=m.name,
                description=m.description,
                duration_seconds=m.duration_seconds,
                instructions=m.instructions or [],
                clinician_approved=m.clinician_approved,
            )
            for m in models
        ]

    def save_session(self, session_obj: TherapySession) -> TherapySession:
        model = TherapySessionModel(
            id=session_obj.id,
            patient_id=session_obj.patient_id,
            exercise_id=session_obj.exercise_id,
            started_at=session_obj.started_at,
            completed=session_obj.completed,
            notes=session_obj.notes,
        )
        self._session.merge(model)
        self._session.flush()
        return session_obj

    def list_sessions(self, patient_id: str) -> list[TherapySession]:
        stmt = select(TherapySessionModel).where(TherapySessionModel.patient_id == patient_id)
        models = self._session.execute(stmt).scalars().all()
        return [
            TherapySession(
                id=m.id,
                patient_id=m.patient_id,
                exercise_id=m.exercise_id,
                started_at=m.started_at,
                completed=m.completed,
                notes=m.notes,
            )
            for m in models
        ]
