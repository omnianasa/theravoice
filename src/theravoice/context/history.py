"""Recent-history context: summarizes recent detected changes for an agent."""

from __future__ import annotations

from dataclasses import dataclass

from theravoice.detection.anomaly_detector import MetricAnomalyResult


@dataclass
class HistoryContext:
    recent_results: list[MetricAnomalyResult]

    def recent_significant_count(self) -> int:
        return sum(1 for r in self.recent_results if r.status == "significant")

    def recent_warning_count(self) -> int:
        return sum(1 for r in self.recent_results if r.status == "warning")
