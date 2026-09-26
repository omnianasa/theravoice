"""Context engine: combines temporal, medication, and history context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from theravoice.context.history import HistoryContext
from theravoice.context.medication import MedicationContext, MedicationProximity
from theravoice.context.rules import describe_medication_proximity
from theravoice.context.temporal import TemporalContext
from theravoice.detection.anomaly_detector import MetricAnomalyResult
from theravoice.schemas.medication import MedicationSchedule


@dataclass
class ContextResult:
    temporal: TemporalContext
    medication_proximities: list[MedicationProximity] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class ContextEngine:
    def __init__(self, medication_context: MedicationContext | None = None) -> None:
        self._medication_context = medication_context or MedicationContext()

    def build_context(
        self,
        observation_time: datetime,
        medication_schedules: list[MedicationSchedule],
        recent_results: list[MetricAnomalyResult],
    ) -> ContextResult:
        temporal = TemporalContext.from_timestamp(observation_time)
        proximities = self._medication_context.find_proximities(
            observation_time, medication_schedules
        )
        notes = describe_medication_proximity(proximities)

        history = HistoryContext(recent_results)
        if history.recent_significant_count() > 0:
            notes.append(
                f"{history.recent_significant_count()} metric(s) showed a significant "
                f"deviation from the personal baseline in this observation."
            )
        elif history.recent_warning_count() > 0:
            notes.append(
                f"{history.recent_warning_count()} metric(s) showed a mild deviation "
                f"from the personal baseline in this observation."
            )

        return ContextResult(temporal=temporal, medication_proximities=proximities, notes=notes)
