"""MonitoringPipeline tests: pulling from a BeeAdapter and incremental cursoring."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from theravoice.ingestion.bee import (
    BeeBindingError,
    BeeConnectionError,
    BeeSyncAdapter,
    MockBeeAdapter,
)
from theravoice.pipeline.monitoring_pipeline import MonitoringPipeline
from theravoice.schemas.patient import Patient
from theravoice.schemas.transcript import TranscriptSegment
from theravoice.storage.repositories.bee_sync import BeeSyncRepository
from theravoice.storage.repositories.patient import PatientRepository


def _make_patient(session_factory, patient_id="mon-p1"):
    with session_factory() as session:
        PatientRepository(session).create(
            Patient(id=patient_id, display_name="Monitoring Patient", consent_data_storage=True)
        )
        session.commit()
    return patient_id


def test_poll_patient_processes_all_seeded_segments(session_factory):
    patient_id = _make_patient(session_factory)
    adapter = MockBeeAdapter()
    adapter.add_transcript(
        TranscriptSegment(
            id="c1",
            patient_id=patient_id,
            text="Good morning, I am feeling okay today.",
            timestamp=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        )
    )
    adapter.add_transcript(
        TranscriptSegment(
            id="c2",
            patient_id=patient_id,
            text="Good afternoon, still doing fine.",
            timestamp=datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc),
        )
    )

    pipeline = MonitoringPipeline(bee_adapter=adapter, session_factory=session_factory)
    results = pipeline.poll_patient(patient_id)
    assert len(results) == 2
    assert all(r.status == "processed" for r in results)


def test_poll_patient_is_incremental_and_does_not_reprocess(session_factory):
    patient_id = _make_patient(session_factory, "mon-p2")
    adapter = MockBeeAdapter()
    adapter.add_transcript(
        TranscriptSegment(
            id="c1",
            patient_id=patient_id,
            text="First conversation.",
            timestamp=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        )
    )

    pipeline = MonitoringPipeline(bee_adapter=adapter, session_factory=session_factory)
    first_results = pipeline.poll_patient(patient_id)
    assert len(first_results) == 1

    # Polling again with no new data should process nothing (the cursor
    # advanced past the just-processed conversation's timestamp).
    second_results = pipeline.poll_patient(patient_id)
    assert second_results == []

    # A genuinely new, later conversation should be picked up.
    adapter.add_transcript(
        TranscriptSegment(
            id="c2",
            patient_id=patient_id,
            text="Second conversation, later on.",
            timestamp=datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc),
        )
    )
    third_results = pipeline.poll_patient(patient_id)
    assert len(third_results) == 1


def test_poll_patient_with_no_data_returns_empty(session_factory):
    patient_id = _make_patient(session_factory, "mon-p3")
    adapter = MockBeeAdapter()
    pipeline = MonitoringPipeline(bee_adapter=adapter, session_factory=session_factory)
    assert pipeline.poll_patient(patient_id) == []


def test_poll_patient_deduplicates_stable_ids_and_keeps_equal_or_older_timestamps(session_factory):
    patient_id = _make_patient(session_factory, "mon-p4")
    adapter = MockBeeAdapter()
    timestamp = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
    adapter.add_transcript(
        TranscriptSegment(
            id="bee:device-1:conversation-2",
            patient_id=patient_id,
            text="Second conversation.",
            timestamp=timestamp,
        )
    )
    pipeline = MonitoringPipeline(
        bee_adapter=adapter,
        session_factory=session_factory,
        source_id="device-1",
        bound_patient_id=patient_id,
    )

    assert len(pipeline.poll_patient(patient_id)) == 1
    assert pipeline.poll_patient(patient_id) == []

    adapter.add_transcript(
        TranscriptSegment(
            id="bee:device-1:conversation-1",
            patient_id=patient_id,
            text="Late-arriving older conversation.",
            timestamp=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        )
    )
    assert len(pipeline.poll_patient(patient_id)) == 1

    with session_factory() as session:
        state = BeeSyncRepository(session).status("device-1")
        assert state is not None
        assert state.patient_id == patient_id
        assert state.status == "success"
        assert state.last_successful_sync_at is not None
        assert state.last_processed_record_id == "bee:device-1:conversation-1"


def test_poll_patient_rejects_a_patient_outside_the_configured_binding(session_factory):
    pipeline = MonitoringPipeline(
        bee_adapter=MockBeeAdapter(),
        session_factory=session_factory,
        source_id="device-1",
        bound_patient_id="bound-patient",
    )

    with pytest.raises(BeeBindingError, match="not bound"):
        pipeline.poll_patient("other-patient")


def test_real_adapter_requires_explicit_binding(session_factory, tmp_path):
    patient_id = _make_patient(session_factory, "mon-unbound")
    pipeline = MonitoringPipeline(
        bee_adapter=BeeSyncAdapter(sync_dir=tmp_path),
        session_factory=session_factory,
    )

    with pytest.raises(BeeBindingError, match="require a configured"):
        pipeline.poll_patient(patient_id)


def test_sync_records_failure_and_retry_processes_unimported_records(session_factory):
    patient_id = _make_patient(session_factory, "mon-failure")
    adapter = MockBeeAdapter()
    pipeline = MonitoringPipeline(
        bee_adapter=adapter,
        session_factory=session_factory,
        source_id="device-failure",
        bound_patient_id=patient_id,
    )

    def fail_get_transcript(*_args, **_kwargs):
        raise BeeConnectionError("proxy down")

    adapter.get_transcript = fail_get_transcript
    with pytest.raises(BeeConnectionError):
        pipeline.poll_patient(patient_id)
    with session_factory() as session:
        state = BeeSyncRepository(session).status("device-failure")
        assert state is not None
        assert state.status == "failed"
        assert state.error_code == "connection_error"

    adapter.get_transcript = MockBeeAdapter.get_transcript.__get__(adapter)
    adapter.add_transcript(
        TranscriptSegment(
            id="bee:device-failure:record-1",
            patient_id=patient_id,
            text="A recovered sync.",
            timestamp=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        )
    )
    assert len(pipeline.poll_patient(patient_id)) == 1


def test_sync_rejects_record_id_owned_by_a_different_patient(session_factory):
    first_patient = _make_patient(session_factory, "mon-owner-a")
    second_patient = _make_patient(session_factory, "mon-owner-b")
    adapter = MockBeeAdapter()
    adapter.add_transcript(
        TranscriptSegment(
            id="bee:source:shared-id",
            patient_id=second_patient,
            text="Must not overwrite another patient's transcript.",
            timestamp=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        )
    )
    # Seed an existing record with the same source ID under the other patient.
    from theravoice.storage.repositories.transcript import TranscriptRepository

    with session_factory() as session:
        TranscriptRepository(session).save(
            TranscriptSegment(
                id="bee:source:shared-id",
                patient_id=first_patient,
                text="Existing private data.",
                timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
            )
        )
        session.commit()

    pipeline = MonitoringPipeline(
        bee_adapter=adapter,
        session_factory=session_factory,
        source_id="source",
        bound_patient_id=second_patient,
    )
    with pytest.raises(BeeBindingError, match="already associated"):
        pipeline.poll_patient(second_patient)

    with session_factory() as session:
        stored = TranscriptRepository(session).list_for_patient(first_patient)
        assert [segment.text for segment in stored] == ["Existing private data."]
