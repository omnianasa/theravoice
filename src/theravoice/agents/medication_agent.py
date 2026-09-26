"""Medication agent: proximity-aware reminders/check-ins. Never changes medication."""

from __future__ import annotations

from theravoice.agents.base import BaseAgent
from theravoice.schemas.action import Action
from theravoice.schemas.agent import AgentRequest, AgentResponse


class MedicationAgent(BaseAgent):
    name = "medication_agent"

    def run(self, request: AgentRequest) -> AgentResponse:
        medication_proximities: list[dict] = request.context.get("medication_proximities", [])
        has_deviation: bool = request.payload.get("has_deviation", False)

        actions: list[Action] = []
        if has_deviation and any(p.get("within_window") for p in medication_proximities):
            actions.append(
                Action(
                    patient_id=request.patient_id,
                    type="REQUEST_CHECK_IN",
                    message=(
                        "Your observation occurred near a scheduled medication window. "
                        "Consider logging how you are feeling."
                    ),
                    priority="normal",
                    requires_confirmation=True,
                    metadata={"medication_proximities": medication_proximities},
                )
            )
        elif has_deviation:
            actions.append(
                Action(
                    patient_id=request.patient_id,
                    type="LOG",
                    message="A deviation from your personal baseline was observed. Consider logging context.",
                    priority="low",
                    requires_confirmation=False,
                    metadata={},
                )
            )

        return AgentResponse(
            agent_name=self.name,
            status="ok",
            events=[],
            actions=actions,
            evidence=[],
            data={},
        )
