"""Stable versioned aliases and metadata for public API consumers."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from theravoice.api.routes.ingestion import ingest_audio, ingest_transcript
from theravoice.config.settings import get_settings
from theravoice.pipeline.analysis_pipeline import AnalysisResult
from theravoice.version import __version__

router = APIRouter(prefix="/api/v1", tags=["api-v1"])


class ApiInfo(BaseModel):
    service: str
    version: str
    api_version: str
    disclaimer: str


class IntegrationInfo(BaseModel):
    name: str
    mode: str
    enabled: bool
    configured: bool


class IntegrationsResponse(BaseModel):
    integrations: list[IntegrationInfo]


@router.get("/info", response_model=ApiInfo)
def api_info() -> ApiInfo:
    return ApiInfo(
        service="theravoice",
        version=__version__,
        api_version="v1",
        disclaimer="These observations are descriptive and are not a diagnosis.",
    )


@router.get("/integrations", response_model=IntegrationsResponse)
def integrations() -> IntegrationsResponse:
    bee = get_settings().bee
    is_mock = bee.mode == "mock"
    is_bound = bool(bee.source_id.strip() and bee.patient_id.strip())
    return IntegrationsResponse(
        integrations=[
            IntegrationInfo(
                name="bee",
                mode=bee.mode,
                enabled=True,
                configured=is_mock or is_bound,
            )
        ]
    )


router.add_api_route(
    "/analyses/transcript",
    ingest_transcript,
    methods=["POST"],
    response_model=AnalysisResult,
    summary="Analyze a transcript",
)
router.add_api_route(
    "/analyses/audio",
    ingest_audio,
    methods=["POST"],
    response_model=AnalysisResult,
    summary="Analyze an audio recording",
)
