"""Agent request/response schemas used by the multi-agent orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from theravoice.schemas.action import Action
from theravoice.schemas.evidence import Evidence
from theravoice.schemas.event import Event


class AgentRequest(BaseModel):
    agent_name: str
    patient_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent_name: str
    status: str = "ok"
    events: list[Event] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)
