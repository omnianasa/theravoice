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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from theravoice.api.dependencies import get_db
from theravoice.ingestion.bee import BeeConnectionError
from theravoice.pipeline.analysis_pipeline import AnalysisResult, PatientNotFoundError
from theravoice.pipeline.monitoring_pipeline import build_monitoring_pipeline
from theravoice.schemas.action import Action
from theravoice.schemas.event import Event
from theravoice.storage.database import get_session_factory
from theravoice.storage.repositories.patient import PatientRepository

router = APIRouter(prefix="/patients/{patient_id}/bee", tags=["bee"])


class BeeSyncResponse(BaseModel):
    patient_id: str
    observations_processed: int
    results: list[AnalysisResult] = Field(default_factory=list)
    new_events: list[Event] = Field(default_factory=list)
    new_actions: list[Action] = Field(default_factory=list)
    message: str


@router.post("/sync", response_model=BeeSyncResponse)
def sync_from_bee(patient_id: str, db: Session = Depends(get_db)) -> BeeSyncResponse:
    if PatientRepository(db).get(patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    pipeline = build_monitoring_pipeline(session_factory=get_session_factory())
    try:
        results = pipeline.poll_patient(patient_id)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BeeConnectionError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"{exc} See docs/bee_integration.md for how to run "
                "`bee login` / `bee sync` / `bee proxy`, or set bee.mode: "
                "mock in config for local testing without a Bee account."
            ),
        ) from exc

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
