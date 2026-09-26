"""Ingestion endpoints: transcript and audio.

These endpoints run the FULL analysis pipeline (biomarker extraction,
baseline, change detection, context, multi-agent orchestration, persistence)
rather than merely storing the input -- see pipeline/analysis_pipeline.py.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_analysis_pipeline, get_db
from theravoice.ingestion.audio_loader import AudioLoadError, load_audio
from theravoice.pipeline.analysis_pipeline import AnalysisPipeline, AnalysisResult, PatientNotFoundError
from theravoice.security.authorization import can_analyze_audio
from theravoice.security.privacy import ConsentError, require_storage_consent
from theravoice.storage.repositories.patient import PatientRepository

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class TranscriptIngestionRequest(BaseModel):
    patient_id: str
    text: str


@router.post("/transcript", response_model=AnalysisResult)
def ingest_transcript(
    payload: TranscriptIngestionRequest,
    pipeline: AnalysisPipeline = Depends(get_analysis_pipeline),
) -> AnalysisResult:
    try:
        return pipeline.run_transcript(patient_id=payload.patient_id, text=payload.text)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/audio", response_model=AnalysisResult)
async def ingest_audio(
    patient_id: str = Form(...),
    text: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    pipeline: AnalysisPipeline = Depends(get_analysis_pipeline),
) -> AnalysisResult:
    """Ingest an audio recording (optionally with an accompanying transcript).

    Patient existence and consent are checked up front (fail fast, before
    spending effort decoding the upload). `AnalysisPipeline.run_audio`
    re-checks consent as defense-in-depth; a `ConsentError` there is mapped
    to HTTP 403 by the app-level error handler.
    """
    patient = PatientRepository(db).get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    try:
        require_storage_consent(patient.consent_data_storage)
        if not can_analyze_audio(patient):
            raise ConsentError("Patient has not granted audio analysis consent.")
    except ConsentError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        loaded = load_audio(tmp_path)
    except AudioLoadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    try:
        return pipeline.run_audio(
            patient_id=patient_id,
            samples=loaded.samples,
            sample_rate=loaded.sample_rate,
            duration_seconds=loaded.duration_seconds,
            text=text,
            source="upload",
        )
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
