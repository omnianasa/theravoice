"""FastAPI dependency providers: DB sessions, auth, pipeline instances."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from theravoice.pipeline.analysis_pipeline import AnalysisPipeline
from theravoice.security.authentication import verify_api_key
from theravoice.storage.database import get_session_factory


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


def get_analysis_pipeline() -> AnalysisPipeline:
    return AnalysisPipeline(session_factory=get_session_factory())


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key."
        )
