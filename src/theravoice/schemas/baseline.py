"""Personal baseline schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BaselineStat(BaseModel):
    mean: float
    std: float
    n: int


class PersonalBaseline(BaseModel):
    patient_id: str
    metrics: dict[str, BaselineStat] = Field(default_factory=dict)
