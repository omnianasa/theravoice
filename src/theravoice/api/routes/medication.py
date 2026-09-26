"""Medication CRUD/read endpoints. Never changes medication automatically."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_db
from theravoice.schemas.medication import Medication, MedicationEvent, MedicationSchedule
from theravoice.storage.repositories.medication import MedicationRepository
from theravoice.storage.repositories.patient import PatientRepository

router = APIRouter(prefix="/patients/{patient_id}/medications", tags=["medication"])


@router.post("", response_model=Medication, status_code=201)
def create_medication(
    patient_id: str, payload: Medication, db: Session = Depends(get_db)
) -> Medication:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    if payload.patient_id != patient_id:
        raise HTTPException(status_code=400, detail="patient_id mismatch between path and body.")
    return MedicationRepository(db).create_medication(payload)


@router.post("/schedules", response_model=MedicationSchedule, status_code=201)
def add_schedule(
    patient_id: str, payload: MedicationSchedule, db: Session = Depends(get_db)
) -> MedicationSchedule:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    return MedicationRepository(db).add_schedule(payload)


@router.get("/schedules", response_model=list[MedicationSchedule])
def list_schedules(patient_id: str, db: Session = Depends(get_db)) -> list[MedicationSchedule]:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    return MedicationRepository(db).list_schedules_for_patient(patient_id)


@router.post("/events", response_model=MedicationEvent, status_code=201)
def log_medication_event(
    patient_id: str, payload: MedicationEvent, db: Session = Depends(get_db)
) -> MedicationEvent:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    if payload.patient_id != patient_id:
        raise HTTPException(status_code=400, detail="patient_id mismatch between path and body.")
    return MedicationRepository(db).log_event(payload)


@router.get("/events", response_model=list[MedicationEvent])
def list_medication_events(patient_id: str, db: Session = Depends(get_db)) -> list[MedicationEvent]:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    return MedicationRepository(db).list_events(patient_id)
