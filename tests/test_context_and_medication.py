"""Context engine and medication-rule tests."""

from __future__ import annotations

from datetime import datetime, timezone

from theravoice.context.engine import ContextEngine
from theravoice.context.medication import MedicationContext
from theravoice.medication.adherence import adherence_rate
from theravoice.schemas.medication import MedicationEvent, MedicationSchedule


def test_medication_proximity_within_window():
    ctx = MedicationContext(window_minutes=60)
    observation_time = datetime(2026, 1, 5, 8, 30, tzinfo=timezone.utc)  # Monday
    schedules = [MedicationSchedule(medication_id="m1", scheduled_time="08:00", days_of_week=[0])]
    proximities = ctx.find_proximities(observation_time, schedules)
    assert len(proximities) == 1
    assert proximities[0].within_window is True


def test_medication_proximity_outside_window():
    ctx = MedicationContext(window_minutes=30)
    observation_time = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    schedules = [MedicationSchedule(medication_id="m1", scheduled_time="08:00", days_of_week=[0])]
    proximities = ctx.find_proximities(observation_time, schedules)
    assert proximities[0].within_window is False


def test_medication_schedule_respects_days_of_week():
    ctx = MedicationContext(window_minutes=60)
    observation_time = datetime(2026, 1, 6, 8, 15, tzinfo=timezone.utc)  # Tuesday
    schedules = [MedicationSchedule(medication_id="m1", scheduled_time="08:00", days_of_week=[0])]
    proximities = ctx.find_proximities(observation_time, schedules)
    assert proximities == []


def test_context_engine_never_claims_causation():
    engine = ContextEngine(MedicationContext(window_minutes=90))
    observation_time = datetime(2026, 1, 5, 8, 10, tzinfo=timezone.utc)
    schedules = [MedicationSchedule(medication_id="m1", scheduled_time="08:00", days_of_week=[0])]
    result = engine.build_context(observation_time, schedules, recent_results=[])
    assert result.notes
    for note in result.notes:
        assert "caused" not in note.lower()
        assert "worn off" not in note.lower()


def test_adherence_rate_computation():
    events = [
        MedicationEvent(id="1", patient_id="p1", medication_id="m1", status="taken"),
        MedicationEvent(id="2", patient_id="p1", medication_id="m1", status="skipped"),
    ]
    assert adherence_rate(events) == 0.5


def test_adherence_rate_none_when_no_events():
    assert adherence_rate([]) is None
