"""Therapy agent: suggests configurable, non-prescriptive speech exercises."""

from __future__ import annotations

from theravoice.agents.base import BaseAgent
from theravoice.schemas.action import Action
from theravoice.schemas.agent import AgentRequest, AgentResponse
from theravoice.therapy.recommendations import recommend_exercises


class TherapyAgent(BaseAgent):
    name = "therapy_agent"

    def __init__(self, require_clinician_approval: bool = True) -> None:
        self._require_clinician_approval = require_clinician_approval

    def run(self, request: AgentRequest) -> AgentResponse:
        has_deviation: bool = request.payload.get("has_deviation", False)
        deviating_metrics: list[str] = request.payload.get("deviating_metrics", [])

        actions: list[Action] = []
        if has_deviation:
            exercises = recommend_exercises(
                deviating_metrics, require_clinician_approval=self._require_clinician_approval
            )
            for exercise in exercises:
                actions.append(
                    Action(
                        patient_id=request.patient_id,
                        type="SUGGEST_EXERCISE",
                        message=f"Consider trying the '{exercise.name}' exercise.",
                        priority="low",
                        requires_confirmation=not exercise.clinician_approved,
                        metadata={"exercise_id": exercise.id},
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
