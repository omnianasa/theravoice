"""Context agent: combines speech/text evidence with temporal & medication context.

Produces contextual interpretation WITHOUT claiming causation (e.g. it will
say a deviation occurred "within" a medication window, never that medication
"caused" it).
"""

from __future__ import annotations

from datetime import datetime, timezone

from theravoice.agents.base import BaseAgent
from theravoice.context.engine import ContextEngine
from theravoice.detection.anomaly_detector import MetricAnomalyResult
from theravoice.schemas.agent import AgentRequest, AgentResponse
from theravoice.schemas.evidence import Evidence
from theravoice.schemas.medication import MedicationSchedule


class ContextAgent(BaseAgent):
    name = "context_agent"

    def __init__(self, context_engine: ContextEngine | None = None) -> None:
        self._context_engine = context_engine or ContextEngine()

    def run(self, request: AgentRequest) -> AgentResponse:
        anomaly_results: list[MetricAnomalyResult] = request.payload.get("anomaly_results", [])
        schedules: list[MedicationSchedule] = request.context.get("medication_schedules", [])
        observation_time: datetime = request.context.get(
            "observation_time", datetime.now(timezone.utc)
        )

        context_result = self._context_engine.build_context(
            observation_time=observation_time,
            medication_schedules=schedules,
            recent_results=anomaly_results,
        )

        evidence = [
            Evidence(
                type="contextual_observation",
                source=self.name,
                description=note,
                value=None,
                confidence=None,
            )
            for note in context_result.notes
        ]

        return AgentResponse(
            agent_name=self.name,
            status="ok",
            events=[],
            actions=[],
            evidence=evidence,
            data={
                "notes": context_result.notes,
                "medication_proximities": [
                    {
                        "medication_id": p.medication_id,
                        "scheduled_time": p.scheduled_time,
                        "minutes_from_scheduled": p.minutes_from_scheduled,
                        "within_window": p.within_window,
                    }
                    for p in context_result.medication_proximities
                ],
            },
        )
