"""Therapy exercise and session endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_db
from theravoice.config.settings import get_settings
from theravoice.schemas.therapy import Exercise, TherapySession
from theravoice.storage.repositories.patient import PatientRepository
from theravoice.storage.repositories.therapy import TherapyRepository
from theravoice.therapy.exercises import list_exercises
from theravoice.therapy.recommendations import recommend_exercises
from theravoice.therapy.sessions import start_session

router = APIRouter(prefix="/patients/{patient_id}/therapy", tags=["therapy"])


def _ensure_patient(db: Session, patient_id: str) -> None:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")


@router.get("/exercises", response_model=list[Exercise])
def get_exercises(patient_id: str, db: Session = Depends(get_db)) -> list[Exercise]:
    _ensure_patient(db, patient_id)
    return list_exercises()


@router.get("/recommendations", response_model=list[Exercise])
def get_recommendations(patient_id: str, db: Session = Depends(get_db)) -> list[Exercise]:
    _ensure_patient(db, patient_id)
    settings = get_settings()
    # Without a specific triggering event, recommend a general baseline set.
    return recommend_exercises([], require_clinician_approval=settings.therapy.require_clinician_approval)


@router.post("/sessions", response_model=TherapySession, status_code=201)
def create_session(
    patient_id: str, exercise_id: str, db: Session = Depends(get_db)
) -> TherapySession:
    _ensure_patient(db, patient_id)
    session_obj = start_session(patient_id, exercise_id)
    return TherapyRepository(db).save_session(session_obj)


@router.get("/sessions", response_model=list[TherapySession])
def list_sessions(patient_id: str, db: Session = Depends(get_db)) -> list[TherapySession]:
    _ensure_patient(db, patient_id)
    return TherapyRepository(db).list_sessions(patient_id)
