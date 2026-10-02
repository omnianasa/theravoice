"""Patient endpoints: create + retrieve."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_db
from theravoice.schemas.patient import (
    Patient,
    PatientCreateRequest,
    PatientLLMConsentUpdateRequest,
)
from theravoice.storage.repositories.patient import PatientRepository

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=Patient, status_code=201)
def create_patient(payload: PatientCreateRequest, db: Session = Depends(get_db)) -> Patient:
    repo = PatientRepository(db)
    if repo.exists(payload.id):
        raise HTTPException(status_code=409, detail=f"Patient '{payload.id}' already exists.")
    patient = Patient(
        id=payload.id,
        display_name=payload.display_name,
        timezone=payload.timezone,
        consent_audio_analysis=payload.consent_audio_analysis,
        consent_data_storage=payload.consent_data_storage,
        consent_llm_processing=payload.consent_llm_processing,
    )
    return repo.create(patient)


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> Patient:
    repo = PatientRepository(db)
    patient = repo.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    return patient


@router.patch("/{patient_id}/consent", response_model=Patient)
def update_llm_consent(
    patient_id: str,
    payload: PatientLLMConsentUpdateRequest,
    db: Session = Depends(get_db),
) -> Patient:
    patient = PatientRepository(db).set_llm_processing_consent(
        patient_id, payload.consent_llm_processing
    )
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    return patient
