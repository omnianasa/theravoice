"""Action schema: assistive, non-clinical actions the system may suggest."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ActionType = Literal[
    "NOTIFY",
    "REMIND",
    "SUGGEST_EXERCISE",
    "LOG",
    "REQUEST_CHECK_IN",
]

Priority = Literal["low", "normal", "high"]


class Action(BaseModel):
    patient_id: str
    type: ActionType
    message: str
    priority: Priority = "normal"
    requires_confirmation: bool = False
    metadata: dict = Field(default_factory=dict)
