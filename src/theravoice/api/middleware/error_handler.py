"""Central exception handlers, mapping domain errors to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from theravoice.pipeline.analysis_pipeline import PatientNotFoundError
from theravoice.security.privacy import ConsentError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PatientNotFoundError)
    async def _patient_not_found_handler(request: Request, exc: PatientNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConsentError)
    async def _consent_error_handler(request: Request, exc: ConsentError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})
