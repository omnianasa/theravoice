"""FastAPI application factory and route registration."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from theravoice.api.middleware.error_handler import register_error_handlers
from theravoice.api.middleware.logging import RequestLoggingMiddleware
from theravoice.api.routes import (
    bee,
    biomarkers,
    events,
    health,
    ingestion,
    medication,
    patients,
    reports,
    therapy,
)
from theravoice.config.settings import get_settings
from theravoice.storage.database import init_db
from theravoice.version import __version__


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
    )

    app.add_middleware(RequestLoggingMiddleware)
    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(patients.router)
    app.include_router(ingestion.router)
    app.include_router(biomarkers.router)
    app.include_router(events.router)
    app.include_router(medication.router)
    app.include_router(therapy.router)
    app.include_router(reports.router)
    app.include_router(bee.router)

    # Serve the static dashboard (dashboard/index.html, app.js, styles.css)
    # at /dashboard. It talks to this same API over fetch() -- see
    # dashboard/app.js. Mounted defensively: if the folder is missing (e.g.
    # a stripped-down deployment), the API still runs fine without it.
    dashboard_dir = Path(__file__).resolve().parents[3] / "dashboard"
    if dashboard_dir.is_dir():
        app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    return app


app = create_app()
