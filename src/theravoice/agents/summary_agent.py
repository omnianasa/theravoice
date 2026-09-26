"""Summary agent: composes a human-readable, non-diagnostic daily summary."""

from __future__ import annotations

from theravoice.agents.base import BaseAgent
from theravoice.schemas.action import Action
from theravoice.schemas.agent import AgentRequest, AgentResponse
from theravoice.schemas.evidence import Evidence

DISCLAIMER = "These observations are descriptive and are not a diagnosis."


class SummaryAgent(BaseAgent):
    name = "summary_agent"

    def run(self, request: AgentRequest) -> AgentResponse:
        evidence: list[Evidence] = request.payload.get("all_evidence", [])
        actions: list[Action] = request.payload.get("all_actions", [])
        context_notes: list[str] = request.payload.get("context_notes", [])

        observations = [e.description for e in evidence if e.type != "contextual_observation"]
        lines = ["Daily Summary", "", "Observations:"]
        lines += [f"- {o}" for o in observations] if observations else ["- No notable deviations observed."]

        if context_notes:
            lines += ["", "Context:"]
            lines += [f"- {n}" for n in context_notes]

        if actions:
            lines += ["", "Suggested actions:"]
            lines += [f"- {a.message}" for a in actions]

        lines += ["", "Important:", DISCLAIMER]
        summary_text = "\n".join(lines)

        return AgentResponse(
            agent_name=self.name,
            status="ok",
            events=[],
            actions=[],
            evidence=[],
            data={"summary_text": summary_text, "disclaimer": DISCLAIMER},
        )
