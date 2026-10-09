"""FastAPI application factory and route registration."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from theravoice.api.dependencies import authenticate_request
from theravoice.api.middleware.error_handler import register_error_handlers
from theravoice.api.middleware.logging import RequestLoggingMiddleware
from theravoice.api.routes import (
    auth,
    bee,
    biomarkers,
    events,
    health,
    ingestion,
    medication,
    patients,
    reports,
    therapy,
    v1,
)
from theravoice.config.settings import get_settings
from theravoice.storage.database import init_db
from theravoice.version import __version__


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: ensure tables exist before the first request is served.
    init_db()
    yield
    # No shutdown work needed today; this is the hook if that changes.


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.logging.level, logging.INFO))

    app = FastAPI(
        title="TheraVoice",
        description=(
            "Non-diagnostic, assistive speech/communication monitoring companion. "
            "Observes changes relative to a patient's own baseline; never diagnoses."
        ),
        version=__version__,
        lifespan=_lifespan,
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-TheraVoice-LLM-Provider",
            "X-TheraVoice-LLM-Model",
            "X-TheraVoice-LLM-API-Key",
        ],
    )
    register_error_handlers(app)

    app.include_router(auth.router)
    protected = {"dependencies": [Depends(authenticate_request)]}
    app.include_router(health.router, **protected)
    app.include_router(patients.router, **protected)
    app.include_router(ingestion.router, **protected)
    app.include_router(biomarkers.router, **protected)
    app.include_router(events.router, **protected)
    app.include_router(medication.router, **protected)
    app.include_router(therapy.router, **protected)
    app.include_router(reports.router, **protected)
    app.include_router(bee.router, **protected)

    # Versioned aliases are additive; legacy routes remain available for
    # existing dashboard and API clients during migration.
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1", **protected)
    app.include_router(patients.router, prefix="/api/v1", **protected)
    app.include_router(ingestion.router, prefix="/api/v1", **protected)
    app.include_router(biomarkers.router, prefix="/api/v1", **protected)
    app.include_router(events.router, prefix="/api/v1", **protected)
    app.include_router(medication.router, prefix="/api/v1", **protected)
    app.include_router(therapy.router, prefix="/api/v1", **protected)
    app.include_router(reports.router, prefix="/api/v1", **protected)
    app.include_router(bee.router, prefix="/api/v1", **protected)
    app.include_router(bee.v1_router, **protected)
    app.include_router(v1.router, dependencies=protected["dependencies"])

    # Serve the compiled React dashboard at /dashboard.
    dashboard_dir = Path(__file__).resolve().parents[3] / "dashboard" / "dist"
    if dashboard_dir.is_dir():
        app.mount(
            "/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard"
        )

    return app


app = create_app()
