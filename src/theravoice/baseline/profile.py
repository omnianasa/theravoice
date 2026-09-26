"""In-memory representation of a patient's rolling observation history.

Persistence is handled by `storage.repositories.biomarker`; this module is
concerned only with the rolling-window math over a list of past values.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricHistory:
    name: str
    values: list[float] = field(default_factory=list)

    def add(self, value: float, window_size: int) -> None:
        self.values.append(value)
        if len(self.values) > window_size:
            self.values = self.values[-window_size:]


@dataclass
class PatientProfile:
    patient_id: str
    histories: dict[str, MetricHistory] = field(default_factory=dict)

    def record(self, metric_name: str, value: float, window_size: int) -> None:
        history = self.histories.setdefault(metric_name, MetricHistory(metric_name))
        history.add(value, window_size)

    def history_for(self, metric_name: str) -> list[float]:
        history = self.histories.get(metric_name)
        return list(history.values) if history else []
