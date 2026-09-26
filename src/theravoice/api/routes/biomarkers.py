"""Biomarker retrieval endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_db
from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue
from theravoice.storage.repositories.patient import PatientRepository
from theravoice.storage.repositories.biomarker import BiomarkerRepository

router = APIRouter(prefix="/patients/{patient_id}/biomarkers", tags=["biomarkers"])


def _ensure_patient(db: Session, patient_id: str) -> None:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")


@router.get("", response_model=list[BiomarkerValue])
def list_biomarkers(patient_id: str, db: Session = Depends(get_db)) -> list[BiomarkerValue]:
    _ensure_patient(db, patient_id)
    return BiomarkerRepository(db).get_all(patient_id)


@router.get("/latest", response_model=BiomarkerSnapshot | None)
def latest_biomarkers(patient_id: str, db: Session = Depends(get_db)) -> BiomarkerSnapshot | None:
    _ensure_patient(db, patient_id)
    return BiomarkerRepository(db).get_latest(patient_id)
