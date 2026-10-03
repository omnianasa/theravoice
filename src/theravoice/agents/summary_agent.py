"""Summary agent: composes a human-readable, non-diagnostic daily summary."""

from __future__ import annotations

import json
import logging

from theravoice.agents.base import BaseAgent
from theravoice.llm.client import LLMClient, LLMError
from theravoice.schemas.action import Action
from theravoice.schemas.agent import AgentRequest, AgentResponse
from theravoice.schemas.evidence import Evidence

logger = logging.getLogger(__name__)
DISCLAIMER = "These observations are descriptive and are not a diagnosis."


class SummaryAgent(BaseAgent):
    name = "summary_agent"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client

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
        generation_status = "deterministic"
        generation_error = None
        llm_client = request.context.get("llm_client", self._llm_client)
        if llm_client is not None and request.context.get("allow_llm_summary", False):
            try:
                generated = llm_client.generate(
                    self._build_prompt(observations, context_notes, actions)
                )
                if generated:
                    summary_text = generated
                    generation_status = "generated"
                    if DISCLAIMER.lower() not in summary_text.lower():
                        summary_text = f"{summary_text.rstrip()}\n\nImportant:\n{DISCLAIMER}"
            except LLMError as error:
                logger.warning("LLM summary generation failed; using deterministic summary: %s", error)
                generation_status = "fallback"
                generation_error = "provider_failure"

        return AgentResponse(
            agent_name=self.name,
            status="ok",
            events=[],
            actions=[],
            evidence=[],
            data={
                "summary_text": summary_text,
                "disclaimer": DISCLAIMER,
                "generation_status": generation_status,
                "generation_error": generation_error,
            },
        )

    @staticmethod
    def _build_prompt(observations: list[str], context_notes: list[str], actions: list[Action]) -> str:
        source_data = {
            "observations": observations,
            "context": context_notes,
            "suggested_actions": [action.message for action in actions],
        }
        return (
            "Write a concise, plain-language daily summary using only the supplied facts. "
            "Do not diagnose, infer causes, add medical advice, or invent details. "
            "Preserve uncertainty and distinguish observations from suggested actions. "
            "Do not include a disclaimer; the application adds its required disclaimer.\n\n"
            f"Facts (JSON):\n{json.dumps(source_data, ensure_ascii=True)}"
        )
