"""Regression test for a real bug found in manual testing on Windows/SQLite:

SQLite has no native timezone-aware datetime type, so a plain
`DateTime(timezone=True)` column silently returns *naive* datetimes on
read-back, even though an aware one was written. The instant that naive
value is compared against any of the timezone-aware datetimes used
everywhere else in this project, Python raises:

    TypeError: can't compare offset-naive and offset-aware datetimes

This bit two real code paths in earlier testing:
  - MonitoringPipeline's auto-cursor (`_last_synced_at`) being compared
    against MockBeeAdapter's aware timestamps.
  - BeeSyncAdapter's freshly-parsed (aware) conversation timestamps being
    compared against that same naive cursor.

Fixed by `UTCDateTime` (storage/models.py), which re-attaches `tzinfo=UTC`
on the way out of the database if the driver dropped it. This test writes a
timestamp, forces a fresh read from the database (not the same in-memory
object), and asserts the round-tripped value is both aware and directly
comparable to a fresh `datetime.now(timezone.utc)`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue
from theravoice.schemas.patient import Patient
from theravoice.storage.repositories.biomarker import BiomarkerRepository
from theravoice.storage.repositories.patient import PatientRepository
from theravoice.storage.repositories.transcript import TranscriptRepository
from theravoice.schemas.transcript import TranscriptSegment


def test_transcript_timestamp_roundtrips_as_timezone_aware(session_factory):
    patient_id = "tz-p1"
    with session_factory() as session:
        PatientRepository(session).create(
            Patient(id=patient_id, display_name="TZ Patient", consent_data_storage=True)
        )
        TranscriptRepository(session).save(
            TranscriptSegment(
                id="seg1",
                patient_id=patient_id,
                text="hello",
                timestamp=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
            )
        )
        session.commit()

    # Fresh session -> forces an actual read from disk, not the cached
    # in-memory object from the write above.
    with session_factory() as fresh_session:
        latest = TranscriptRepository(fresh_session).get_latest_timestamp(patient_id)

    assert latest is not None
    assert latest.tzinfo is not None
    # This comparison is exactly what previously raised
    # "can't compare offset-naive and offset-aware datetimes".
    assert latest < datetime.now(timezone.utc)
    assert latest == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_biomarker_snapshot_timestamp_roundtrips_as_timezone_aware(session_factory):
    patient_id = "tz-p2"
    with session_factory() as session:
        PatientRepository(session).create(
            Patient(id=patient_id, display_name="TZ Patient 2", consent_data_storage=True)
        )
        BiomarkerRepository(session).save_snapshot(
            BiomarkerSnapshot(
                patient_id=patient_id,
                timestamp=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
                values=[BiomarkerValue(name="a", value=1.0, source="text", available=True)],
            )
        )
        session.commit()

    with session_factory() as fresh_session:
        latest = BiomarkerRepository(fresh_session).get_latest(patient_id)

    assert latest is not None
    assert latest.timestamp.tzinfo is not None
    assert latest.timestamp <= datetime.now(timezone.utc)
