"""MonitoringPipeline tests: pulling from a BeeAdapter and incremental cursoring."""

from __future__ import annotations

from datetime import datetime, timezone

from theravoice.ingestion.bee import MockBeeAdapter
from theravoice.pipeline.monitoring_pipeline import MonitoringPipeline
from theravoice.schemas.patient import Patient
from theravoice.schemas.transcript import TranscriptSegment
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
