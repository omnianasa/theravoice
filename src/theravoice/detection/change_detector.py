"""Runs anomaly detection across all available biomarkers in a snapshot."""

from __future__ import annotations

from theravoice.detection.anomaly_detector import AnomalyDetector, MetricAnomalyResult
from theravoice.schemas.baseline import PersonalBaseline
from theravoice.schemas.biomarker import BiomarkerSnapshot


class ChangeDetector:
    def __init__(self, anomaly_detector: AnomalyDetector) -> None:
        self._anomaly_detector = anomaly_detector

    def detect(
        self, snapshot: BiomarkerSnapshot, baseline: PersonalBaseline
    ) -> list[MetricAnomalyResult]:
        results: list[MetricAnomalyResult] = []
        for value in snapshot.values:
            if not value.available or value.value is None:
                continue
            results.append(
                self._anomaly_detector.evaluate_metric(value.name, float(value.value), baseline)
            )
        return results

    @staticmethod
    def significant_results(
        results: list[MetricAnomalyResult],
    ) -> list[MetricAnomalyResult]:
        return [r for r in results if r.status in ("warning", "significant")]
