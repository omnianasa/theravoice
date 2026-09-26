"""Event retrieval endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_db
from theravoice.schemas.event import Event
from theravoice.storage.repositories.event import EventRepository
from theravoice.storage.repositories.patient import PatientRepository

router = APIRouter(prefix="/patients/{patient_id}/events", tags=["events"])


@router.get("", response_model=list[Event])
def list_events(patient_id: str, db: Session = Depends(get_db)) -> list[Event]:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    return EventRepository(db).list_for_patient(patient_id)
