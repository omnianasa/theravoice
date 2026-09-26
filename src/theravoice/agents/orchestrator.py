"""Multi-agent orchestrator.

Flow:
  Input -> SpeechAgent -> TextAgent -> ContextAgent -> MedicationAgent
        -> TherapyAgent -> SummaryAgent -> Combined AgentResponse
"""

from __future__ import annotations

from datetime import datetime, timezone

from theravoice.agents.context_agent import ContextAgent
from theravoice.agents.manifest import load_agent_manifest
from theravoice.agents.medication_agent import MedicationAgent
from theravoice.agents.speech_agent import SpeechAgent
from theravoice.agents.summary_agent import SummaryAgent
from theravoice.agents.text_agent import TextAgent
from theravoice.agents.therapy_agent import TherapyAgent
from theravoice.detection.anomaly_detector import MetricAnomalyResult
from theravoice.schemas.action import Action
from theravoice.schemas.agent import AgentRequest, AgentResponse
from theravoice.schemas.evidence import Evidence
from theravoice.schemas.event import Event
from theravoice.schemas.medication import MedicationSchedule


class AgentOrchestrator:
    def __init__(
        self,
        speech_agent: SpeechAgent | None = None,
        text_agent: TextAgent | None = None,
        context_agent: ContextAgent | None = None,
        medication_agent: MedicationAgent | None = None,
        therapy_agent: TherapyAgent | None = None,
        summary_agent: SummaryAgent | None = None,
        agent_manifest: dict[str, bool] | None = None,
    ) -> None:
        self.speech_agent = speech_agent or SpeechAgent()
        self.text_agent = text_agent or TextAgent()
        self.context_agent = context_agent or ContextAgent()
        self.medication_agent = medication_agent or MedicationAgent()
        self.therapy_agent = therapy_agent or TherapyAgent()
        self.summary_agent = summary_agent or SummaryAgent()
        # agents/manifest.yaml (top-level, operator-facing config) can
        # disable individual agents without a code change. Missing entries
        # default to enabled -- see agents/manifest.py.
        self._manifest = agent_manifest if agent_manifest is not None else load_agent_manifest()

    def _enabled(self, agent_name: str) -> bool:
        return self._manifest.get(agent_name, True)

    def _run_agent(self, agent, request: AgentRequest) -> AgentResponse:
        if not self._enabled(agent.name):
            return AgentResponse(agent_name=agent.name, status="disabled")
        return agent.run(request)

    def run(
        self,
        patient_id: str,
        anomaly_results: list[MetricAnomalyResult],
        medication_schedules: list[MedicationSchedule] | None = None,
        observation_time: datetime | None = None,
    ) -> AgentResponse:
        observation_time = observation_time or datetime.now(timezone.utc)
        medication_schedules = medication_schedules or []

        base_payload = {"anomaly_results": anomaly_results}

        speech_response = self._run_agent(
            self.speech_agent,
            AgentRequest(
                agent_name=self.speech_agent.name,
                patient_id=patient_id,
                payload=base_payload,
                context={},
            ),
        )
        text_response = self._run_agent(
            self.text_agent,
            AgentRequest(
                agent_name=self.text_agent.name,
                patient_id=patient_id,
                payload=base_payload,
                context={},
            ),
        )

        all_events: list[Event] = list(speech_response.events) + list(text_response.events)
        all_evidence: list[Evidence] = list(speech_response.evidence) + list(text_response.evidence)
        has_deviation = len(all_events) > 0
        deviating_metrics = [m for e in all_events for m in e.metadata.get("deviating_metrics", [])]

        context_response = self._run_agent(
            self.context_agent,
            AgentRequest(
                agent_name=self.context_agent.name,
                patient_id=patient_id,
                payload={"anomaly_results": anomaly_results},
                context={
                    "medication_schedules": medication_schedules,
                    "observation_time": observation_time,
                },
            ),
        )
        all_evidence += list(context_response.evidence)
        context_notes: list[str] = context_response.data.get("notes", [])

        medication_response = self._run_agent(
            self.medication_agent,
            AgentRequest(
                agent_name=self.medication_agent.name,
                patient_id=patient_id,
                payload={"has_deviation": has_deviation},
                context={
                    "medication_proximities": context_response.data.get(
                        "medication_proximities", []
                    )
                },
            ),
        )

        therapy_response = self._run_agent(
            self.therapy_agent,
            AgentRequest(
                agent_name=self.therapy_agent.name,
                patient_id=patient_id,
                payload={"has_deviation": has_deviation, "deviating_metrics": deviating_metrics},
                context={},
            ),
        )

        all_actions: list[Action] = list(medication_response.actions) + list(
            therapy_response.actions
        )

        summary_response = self._run_agent(
            self.summary_agent,
            AgentRequest(
                agent_name=self.summary_agent.name,
                patient_id=patient_id,
                payload={
                    "all_evidence": all_evidence,
                    "all_actions": all_actions,
                    "context_notes": context_notes,
                },
                context={},
            ),
        )

        return AgentResponse(
            agent_name="orchestrator",
            status="ok",
            events=all_events,
            actions=all_actions,
            evidence=all_evidence,
            data={
                "summary_text": summary_response.data.get("summary_text", ""),
                "context_notes": context_notes,
            },
        )
