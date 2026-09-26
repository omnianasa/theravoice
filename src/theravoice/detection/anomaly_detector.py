"""Z-score based per-metric anomaly detection against a personal baseline."""

from __future__ import annotations

from dataclasses import dataclass

from theravoice.detection.confidence import ConfidenceEstimator
from theravoice.detection.thresholds import ThresholdManager
from theravoice.schemas.baseline import PersonalBaseline


@dataclass
class MetricAnomalyResult:
    metric_name: str
    current_value: float
    baseline_mean: float | None
    baseline_std: float | None
    z_score: float | None
    status: str  # normal | warning | significant | insufficient_data
    confidence: float


class AnomalyDetector:
    def __init__(
        self,
        threshold_manager: ThresholdManager | None = None,
        confidence_estimator: ConfidenceEstimator | None = None,
        minimum_observations: int = 5,
    ) -> None:
        self._thresholds = threshold_manager or ThresholdManager()
        self._confidence = confidence_estimator or ConfidenceEstimator()
        self._minimum_observations = minimum_observations

    def evaluate_metric(
        self, metric_name: str, current_value: float, baseline: PersonalBaseline
    ) -> MetricAnomalyResult:
        stat = baseline.metrics.get(metric_name)
        if stat is None:
            return MetricAnomalyResult(
                metric_name=metric_name,
                current_value=current_value,
                baseline_mean=None,
                baseline_std=None,
                z_score=None,
                status="insufficient_data",
                confidence=0.0,
            )

        if stat.std == 0:
            # No variation observed historically; treat any difference as
            # informative but avoid a divide-by-zero.
            z_score = 0.0 if current_value == stat.mean else float("inf")
        else:
            z_score = (current_value - stat.mean) / stat.std

        abs_z = abs(z_score) if z_score not in (float("inf"), float("-inf")) else float("inf")
        status = self._thresholds.classify(abs_z)
        confidence = self._confidence.estimate(stat.n, self._minimum_observations)

        return MetricAnomalyResult(
            metric_name=metric_name,
            current_value=current_value,
            baseline_mean=stat.mean,
            baseline_std=stat.std,
            z_score=None if z_score == float("inf") else z_score,
            status=status,
            confidence=confidence,
        )
