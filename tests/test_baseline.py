"""Baseline computation tests: insufficient_data behavior and updates."""

from __future__ import annotations

from theravoice.baseline.personal import (
    BASELINE_STATUS_INSUFFICIENT,
    BASELINE_STATUS_OK,
    compute_baseline,
)
from theravoice.baseline.profile import PatientProfile
from theravoice.baseline.updater import BaselineUpdater
from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue


def test_insufficient_data_when_below_minimum():
    profile = PatientProfile(patient_id="p1")
    profile.record("word_count", 10.0, window_size=20)
    profile.record("word_count", 12.0, window_size=20)

    baseline, status = compute_baseline(profile, minimum_observations=5)
    assert status["word_count"] == BASELINE_STATUS_INSUFFICIENT
    assert "word_count" not in baseline.metrics


def test_baseline_ok_once_minimum_reached():
    profile = PatientProfile(patient_id="p1")
    for v in [10.0, 11.0, 9.0, 10.5, 10.0]:
        profile.record("word_count", v, window_size=20)

    baseline, status = compute_baseline(profile, minimum_observations=5)
    assert status["word_count"] == BASELINE_STATUS_OK
    assert baseline.metrics["word_count"].n == 5


def test_baseline_updater_records_available_values_only():
    profile = PatientProfile(patient_id="p1")
    updater = BaselineUpdater(rolling_window_size=20, update_enabled=True)
    snapshot = BiomarkerSnapshot(
        patient_id="p1",
        values=[
            BiomarkerValue(name="a", value=1.0, source="text", available=True),
            BiomarkerValue(name="b", value=None, source="text", available=False),
        ],
    )
    updater.update(profile, snapshot)
    assert profile.history_for("a") == [1.0]
    assert profile.history_for("b") == []


def test_baseline_updater_disabled_does_not_record():
    profile = PatientProfile(patient_id="p1")
    updater = BaselineUpdater(rolling_window_size=20, update_enabled=False)
    snapshot = BiomarkerSnapshot(
        patient_id="p1", values=[BiomarkerValue(name="a", value=1.0, source="text", available=True)]
    )
    updater.update(profile, snapshot)
    assert profile.history_for("a") == []


def test_rolling_window_truncates_history():
    profile = PatientProfile(patient_id="p1")
    for i in range(10):
        profile.record("a", float(i), window_size=3)
    assert profile.history_for("a") == [7.0, 8.0, 9.0]
