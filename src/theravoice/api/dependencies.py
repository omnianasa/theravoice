"""FastAPI dependency providers: DB sessions, auth, pipeline instances."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from theravoice.pipeline.analysis_pipeline import AnalysisPipeline
from theravoice.security.authentication import verify_api_key
from theravoice.security.user_auth import authenticate_session
from theravoice.storage.database import get_session_factory
from theravoice.storage.models import PatientModel


def get_db() -> Iterator[Session]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DB_SESSION = Depends(get_db)


def get_analysis_pipeline() -> AnalysisPipeline:
    return AnalysisPipeline(session_factory=get_session_factory())


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key."
        )


def authenticate_request(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    db: Session = DB_SESSION,
) -> None:
    """Accept a user session or the configured service API key."""
    if authorization is not None:
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid bearer token is required.",
            )
        user = authenticate_session(db, token)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session is invalid or expired.",
            )
        request.state.user_id = user.id
        _require_owned_patient(request, db, user.id)
        return

    if verify_api_key(x_api_key):
        request.state.user_id = None
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key."
    )


def require_owned_patient(db: Session, user_id: str, patient_id: str) -> None:
    patient = db.get(PatientModel, patient_id)
    if patient is None or patient.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")


def _require_owned_patient(request: Request, db: Session, user_id: str) -> None:
    patient_id = request.path_params.get("patient_id")
    if patient_id is not None:
        require_owned_patient(db, user_id, patient_id)
