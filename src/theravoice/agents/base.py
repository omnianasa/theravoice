"""Base class every agent must inherit from."""

from __future__ import annotations

from abc import ABC, abstractmethod

from theravoice.schemas.agent import AgentRequest, AgentResponse


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    def run(self, request: AgentRequest) -> AgentResponse:
        """Process an AgentRequest and return a structured AgentResponse."""
