"""Change/anomaly detection tests."""

from __future__ import annotations

from theravoice.detection.anomaly_detector import AnomalyDetector
from theravoice.detection.change_detector import ChangeDetector
from theravoice.detection.confidence import ConfidenceEstimator
from theravoice.detection.thresholds import ThresholdManager
from theravoice.schemas.baseline import BaselineStat, PersonalBaseline
from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue


def _detector(warning_z=1.5, significant_z=2.0, minimum_observations=5):
    return AnomalyDetector(
        threshold_manager=ThresholdManager(warning_z=warning_z, significant_z=significant_z),
        confidence_estimator=ConfidenceEstimator(),
        minimum_observations=minimum_observations,
    )


def test_normal_when_within_threshold():
    baseline = PersonalBaseline(patient_id="p1", metrics={"a": BaselineStat(mean=10.0, std=2.0, n=10)})
    result = _detector().evaluate_metric("a", 10.5, baseline)
    assert result.status == "normal"


def test_significant_when_far_from_mean():
    baseline = PersonalBaseline(patient_id="p1", metrics={"a": BaselineStat(mean=10.0, std=1.0, n=10)})
    result = _detector().evaluate_metric("a", 15.0, baseline)
    assert result.status == "significant"
    assert result.z_score == 5.0


def test_insufficient_data_when_metric_missing_from_baseline():
    baseline = PersonalBaseline(patient_id="p1", metrics={})
    result = _detector().evaluate_metric("a", 5.0, baseline)
    assert result.status == "insufficient_data"
    assert result.z_score is None


def test_zero_std_handled_without_crash():
    baseline = PersonalBaseline(patient_id="p1", metrics={"a": BaselineStat(mean=5.0, std=0.0, n=10)})
    same = _detector().evaluate_metric("a", 5.0, baseline)
    assert same.status == "normal"
    different = _detector().evaluate_metric("a", 6.0, baseline)
    assert different.status == "significant"


def test_change_detector_skips_unavailable_values():
    baseline = PersonalBaseline(patient_id="p1", metrics={"a": BaselineStat(mean=1.0, std=1.0, n=10)})
    snapshot = BiomarkerSnapshot(
        patient_id="p1",
        values=[
            BiomarkerValue(name="a", value=1.0, source="text", available=True),
            BiomarkerValue(name="b", value=None, source="text", available=False),
        ],
    )
    results = ChangeDetector(_detector()).detect(snapshot, baseline)
    assert len(results) == 1
    assert results[0].metric_name == "a"
