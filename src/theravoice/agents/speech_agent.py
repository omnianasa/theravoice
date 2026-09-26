"""Speech agent: inspects speech biomarkers and compares them to baseline."""

from __future__ import annotations

from theravoice.agents.base import BaseAgent
from theravoice.detection.anomaly_detector import MetricAnomalyResult
from theravoice.schemas.action import Action
from theravoice.schemas.agent import AgentRequest, AgentResponse
from theravoice.schemas.evidence import Evidence
from theravoice.schemas.event import Event

_SPEECH_METRICS = {
    "pause_count",
    "pause_ratio",
    "mean_pause_duration_seconds",
    "max_pause_duration_seconds",
    "long_pause_count",
    "f0_mean_hz",
    "f0_std_hz",
    "pitch_coefficient_of_variation",
    "rms_db",
    "zero_crossing_rate",
    "spectral_centroid_hz",
    "speech_rate_wpm",
    "articulation_rate_wpm",
}


class SpeechAgent(BaseAgent):
    name = "speech_agent"

    def run(self, request: AgentRequest) -> AgentResponse:
        anomaly_results: list[MetricAnomalyResult] = request.payload.get("anomaly_results", [])
        speech_results = [r for r in anomaly_results if r.metric_name in _SPEECH_METRICS]
        deviations = [r for r in speech_results if r.status in ("warning", "significant")]

        evidence: list[Evidence] = []
        for r in deviations:
            direction = "higher" if (r.z_score or 0) > 0 else "lower"
            evidence.append(
                Evidence(
                    type="speech_biomarker_deviation",
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
                    type="speech_pattern_change",
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
