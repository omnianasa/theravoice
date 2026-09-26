"""Shared pytest fixtures: an isolated in-memory-ish SQLite DB per test session."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _test_environment():
    """Force THERAVOICE_ENV=testing and point the DB at a temp file for the
    whole test session, before any theravoice module is imported/cached."""
    tmp_dir = tempfile.mkdtemp(prefix="theravoice_test_")
    db_path = Path(tmp_dir) / "theravoice_test.db"
    os.environ["THERAVOICE_ENV"] = "testing"
    os.environ["THERAVOICE_DATABASE_URL"] = f"sqlite:///{db_path}"
    yield


@pytest.fixture()
def session_factory():
    from theravoice.config.settings import reload_settings
    from theravoice.storage.database import get_session_factory, init_db, reset_db_state

    reset_db_state()
    reload_settings()
    init_db()
    return get_session_factory()


@pytest.fixture()
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory):
    from fastapi.testclient import TestClient

    from theravoice.api.app import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
