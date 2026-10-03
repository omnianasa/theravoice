"""Repository persistence round-trip tests (require a DB session)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text

from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue
from theravoice.schemas.event import Event
from theravoice.schemas.evidence import Evidence
from theravoice.schemas.patient import Patient
from theravoice.storage.database import (
    _ensure_patient_llm_consent_column,
    _ensure_patient_owner_column,
)
from theravoice.storage.models import Base
from theravoice.storage.repositories.biomarker import BiomarkerRepository
from theravoice.storage.repositories.event import EventRepository
from theravoice.storage.repositories.patient import PatientRepository


def test_patient_repository_round_trip(db_session):
    repo = PatientRepository(db_session)
    patient = Patient(id="p1", display_name="Test", consent_data_storage=True)
    repo.create(patient)
    db_session.commit()

    fetched = repo.get("p1")
    assert fetched is not None
    assert fetched.display_name == "Test"
    assert fetched.consent_llm_processing is False
    assert repo.exists("p1") is True
    assert repo.exists("nope") is False


def test_existing_patient_table_gets_default_false_llm_consent_column():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE patients (id VARCHAR PRIMARY KEY)"))

    _ensure_patient_llm_consent_column(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("patients")}
    assert "consent_llm_processing" in columns
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO patients (id) VALUES ('p1')"))
        consent = connection.execute(
            text("SELECT consent_llm_processing FROM patients WHERE id = 'p1'")
        ).scalar_one()
    assert consent is False or consent == 0
    engine.dispose()


def test_existing_patient_table_gets_nullable_account_owner_column():
    engine = create_engine("sqlite://")
    Base.metadata.tables["users"].create(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE patients (id VARCHAR PRIMARY KEY)"))

    _ensure_patient_owner_column(engine)

    columns = {column["name"]: column for column in inspect(engine).get_columns("patients")}
    assert "owner_user_id" in columns
    assert columns["owner_user_id"]["nullable"] is True
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO patients (id) VALUES ('legacy-patient')"))
        owner = connection.execute(
            text("SELECT owner_user_id FROM patients WHERE id = 'legacy-patient'")
        ).scalar_one()
    assert owner is None
    engine.dispose()


def test_biomarker_repository_save_and_get_latest(db_session):
    repo = BiomarkerRepository(db_session)
    snapshot = BiomarkerSnapshot(
        patient_id="p1",
        timestamp=datetime.now(timezone.utc),
        values=[BiomarkerValue(name="word_count", value=7.0, source="text", available=True)],
    )
    repo.save_snapshot(snapshot)
    db_session.commit()

    latest = repo.get_latest("p1")
    assert latest is not None
    assert latest.as_dict()["word_count"] == 7.0


def test_biomarker_repository_history(db_session):
    repo = BiomarkerRepository(db_session)
    for v in [1.0, 2.0, 3.0]:
        snapshot = BiomarkerSnapshot(
            patient_id="p1", values=[BiomarkerValue(name="a", value=v, source="text", available=True)]
        )
        repo.save_snapshot(snapshot)
    db_session.commit()

    history = repo.get_history("p1", "a")
    assert history == [1.0, 2.0, 3.0]


def test_event_repository_round_trip(db_session):
    repo = EventRepository(db_session)
    event = Event(
        type="speech_pattern_change",
        patient_id="p1",
        severity="warning",
        evidence=[Evidence(type="x", source="test", description="desc")],
    )
    repo.save(event)
    db_session.commit()

    events = repo.list_for_patient("p1")
    assert len(events) == 1
    assert events[0].type == "speech_pattern_change"
    assert events[0].evidence[0].description == "desc"
