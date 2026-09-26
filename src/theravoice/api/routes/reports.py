"""Report endpoints: daily / timeline / clinical summaries."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_db
from theravoice.reporting.clinical_summary import build_clinical_summary
from theravoice.reporting.daily_summary import build_daily_summary
from theravoice.reporting.timeline import build_timeline
from theravoice.schemas.report import ClinicalSummary, DailySummary, Timeline
from theravoice.storage.repositories.patient import PatientRepository

router = APIRouter(prefix="/patients/{patient_id}/reports", tags=["reports"])


def _ensure_patient(db: Session, patient_id: str) -> None:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")


@router.get("/daily", response_model=DailySummary)
def daily_report(
    patient_id: str,
    day: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DailySummary:
    _ensure_patient(db, patient_id)
    target_day = day or datetime.now(timezone.utc).date()
    return build_daily_summary(db, patient_id, target_day)


@router.get("/timeline", response_model=Timeline)
def timeline_report(patient_id: str, db: Session = Depends(get_db)) -> Timeline:
    _ensure_patient(db, patient_id)
    return build_timeline(db, patient_id)


@router.get("/clinical", response_model=ClinicalSummary)
def clinical_report(patient_id: str, db: Session = Depends(get_db)) -> ClinicalSummary:
    _ensure_patient(db, patient_id)
    return build_clinical_summary(db, patient_id)
