"""Text agent: inspects text/language biomarkers and compares them to baseline."""

from __future__ import annotations

from theravoice.agents.base import BaseAgent
from theravoice.detection.anomaly_detector import MetricAnomalyResult
from theravoice.schemas.agent import AgentRequest, AgentResponse
from theravoice.schemas.evidence import Evidence
from theravoice.schemas.event import Event

_TEXT_METRICS = {
    "word_count",
    "sentence_count",
    "average_sentence_length",
    "character_count",
    "token_count",
    "unique_token_count",
    "lexical_diversity",
    "hesitation_count",
    "immediate_word_repetitions",
    "repeated_two_word_phrases",
    "response_latency_seconds",
}


class TextAgent(BaseAgent):
    name = "text_agent"

    def run(self, request: AgentRequest) -> AgentResponse:
        anomaly_results: list[MetricAnomalyResult] = request.payload.get("anomaly_results", [])
        text_results = [r for r in anomaly_results if r.metric_name in _TEXT_METRICS]
        deviations = [r for r in text_results if r.status in ("warning", "significant")]

        evidence: list[Evidence] = []
        for r in deviations:
            direction = "higher" if (r.z_score or 0) > 0 else "lower"
            evidence.append(
                Evidence(
                    type="text_biomarker_deviation",
                    source=self.name,
                    description=(
                        f"{r.metric_name} was {direction} than the recent personal "
                        f"baseline ({r.status})."
                    ),
                    value=r.current_value,
                    confidence=r.confidence,
                )
            )

        events: list[Event] = []
        if deviations:
            severity = "significant" if any(r.status == "significant" for r in deviations) else "warning"
            events.append(
                Event(
                    type="text_pattern_change",
                    patient_id=request.patient_id,
                    severity=severity,
                    evidence=evidence,
                    metadata={"deviating_metrics": [r.metric_name for r in deviations]},
                )
            )

        return AgentResponse(
            agent_name=self.name,
            status="ok",
            events=events,
            actions=[],
            evidence=evidence,
            data={"deviation_count": len(deviations)},
        )
