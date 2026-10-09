"""Bee sync endpoint: pulls real data from the configured Bee channel
(`bee.mode`: mock | sync | proxy -- see docs/bee_integration.md) and runs it
through the full analysis pipeline for a patient.

This is the concrete "does something useful with real Bee data" action: a
person (or the dashboard's "Sync from Bee" button) calls this, and gets back
exactly what changed in their speech patterns since the last sync, plus any
assistive actions (check-in suggestions, exercise suggestions) -- not just a
raw data dump.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from theravoice.api.dependencies import DB_SESSION
from theravoice.config.settings import get_settings
from theravoice.ingestion.bee import BeeBindingError, BeeConnectionError
from theravoice.pipeline.analysis_pipeline import AnalysisResult, PatientNotFoundError
from theravoice.pipeline.monitoring_pipeline import build_monitoring_pipeline
from theravoice.schemas.action import Action
from theravoice.schemas.event import Event
from theravoice.storage.database import get_session_factory
from theravoice.storage.models import BeeSyncStateModel
from theravoice.storage.repositories.bee_sync import BeeSyncRepository
from theravoice.storage.repositories.patient import PatientRepository

router = APIRouter(prefix="/patients/{patient_id}/bee", tags=["bee"])
v1_router = APIRouter(
    prefix="/api/v1/patients/{patient_id}/integrations/bee",
    tags=["bee"],
)


class BeeSyncResponse(BaseModel):
    patient_id: str
    observations_processed: int
    results: list[AnalysisResult] = Field(default_factory=list)
    new_events: list[Event] = Field(default_factory=list)
    new_actions: list[Action] = Field(default_factory=list)
    message: str


class BeeSyncStatusResponse(BaseModel):
    patient_id: str
    mode: str
    source_configured: bool
    status: str
    last_attempt_at: datetime | None = None
    last_successful_sync_at: datetime | None = None
    error_code: str | None = None


@router.post("/sync", response_model=BeeSyncResponse)
def sync_from_bee(patient_id: str, db: Session = DB_SESSION) -> BeeSyncResponse:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    try:
        pipeline = build_monitoring_pipeline(session_factory=get_session_factory())
        results = pipeline.poll_patient(patient_id)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BeeBindingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BeeConnectionError:
        raise HTTPException(
            status_code=502,
            detail=(
                "Bee sync is unavailable. Verify the local Bee CLI session and "
                "proxy/export configuration; see docs/bee_integration.md, or "
                "set bee.mode: mock for local testing without a Bee account."
            ),
        )

    new_events = [event for result in results for event in result.events]
    new_actions = [action for result in results for action in result.actions]

    if not results:
        message = "No new Bee conversations since the last sync."
    elif not new_events:
        message = (
            f"Processed {len(results)} new conversation(s) from Bee. "
            "No notable deviations from your personal baseline were observed."
        )
    else:
        message = (
            f"Processed {len(results)} new conversation(s) from Bee. "
            f"{len(new_events)} observation(s) differed from your personal baseline -- "
            "see new_events/new_actions below. This is descriptive, not a diagnosis."
        )

    return BeeSyncResponse(
        patient_id=patient_id,
        observations_processed=len(results),
        results=results,
        new_events=new_events,
        new_actions=new_actions,
        message=message,
    )


@v1_router.post("/sync", response_model=BeeSyncResponse)
def sync_from_bee_v1(patient_id: str, db: Session = DB_SESSION) -> BeeSyncResponse:
    """Versioned Bee synchronization endpoint; legacy `/patients/{id}/bee/sync` remains."""
    return sync_from_bee(patient_id, db)


@v1_router.get("/status", response_model=BeeSyncStatusResponse)
def bee_sync_status(patient_id: str, db: Session = DB_SESSION) -> BeeSyncStatusResponse:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    settings = get_settings().bee
    is_mock = settings.mode == "mock"
    configured_source_id = settings.source_id.strip()
    configured_patient_id = settings.patient_id.strip()
    is_bound = bool(configured_source_id and configured_patient_id)
    if is_bound and configured_patient_id != patient_id:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    state: BeeSyncStateModel | None = None
    if is_bound:
        state = BeeSyncRepository(db).status(configured_source_id)
        if state is not None and state.patient_id != patient_id:
            raise HTTPException(status_code=409, detail="Bee source binding requires review.")

    return BeeSyncStatusResponse(
        patient_id=patient_id,
        mode=settings.mode,
        source_configured=is_mock or is_bound,
        status=(
            state.status
            if state is not None
            else ("not_configured" if not is_mock and not is_bound else "never_synced")
        ),
        last_attempt_at=state.last_attempt_at if state is not None else None,
        last_successful_sync_at=state.last_successful_sync_at if state is not None else None,
        error_code=state.error_code if state is not None else None,
    )
