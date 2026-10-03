"""Database engine/session management.

Uses SQLAlchemy 2's sessionmaker. SQLite is used for local development; the
`url` in config can be swapped for another SQLAlchemy-compatible backend in
production without touching application code, as long as the dialect
supports the same feature set used here.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateColumn

from theravoice.config.settings import get_settings
from theravoice.storage.models import Base

_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def _ensure_sqlite_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    db_path = url.replace("sqlite:///", "", 1)
    if db_path in (":memory:", ""):
        return
    Path(db_path).resolve().parent.mkdir(parents=True, exist_ok=True)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _ensure_sqlite_dir(settings.database.url)
        connect_args = {"check_same_thread": False} if settings.database.url.startswith("sqlite") else {}
        _engine = create_engine(
            settings.database.url, echo=settings.database.echo, connect_args=connect_args
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def init_db() -> None:
    """Create missing tables and apply small additive schema upgrades."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_patient_llm_consent_column(engine)
    _ensure_patient_owner_column(engine)


def _ensure_patient_llm_consent_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "patients" not in inspector.get_table_names():
        return
    column = "consent_llm_processing"
    if column in {item["name"] for item in inspector.get_columns("patients")}:
        return

    column_definition = CreateColumn(Base.metadata.tables["patients"].c[column]).compile(
        dialect=engine.dialect
    )
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE patients ADD COLUMN {column_definition}"))


def _ensure_patient_owner_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "patients" not in inspector.get_table_names():
        return
    column = "owner_user_id"
    if column in {item["name"] for item in inspector.get_columns("patients")}:
        return

    column_definition = CreateColumn(Base.metadata.tables["patients"].c[column]).compile(
        dialect=engine.dialect
    )
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE patients ADD COLUMN {column_definition}"))


def reset_db_state() -> None:
    """Clear cached engine/session factory (used by tests to reload config)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


@contextmanager
def session_scope(session_factory: sessionmaker | None = None) -> Iterator[Session]:
    factory = session_factory or get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
