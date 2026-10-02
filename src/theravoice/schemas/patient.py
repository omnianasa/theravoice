"""Patient schema."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Patient(BaseModel):
    id: str
    display_name: str
    timezone: str = "UTC"
    consent_audio_analysis: bool = False
    consent_data_storage: bool = False
    consent_llm_processing: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PatientCreateRequest(BaseModel):
    id: str
    display_name: str
    timezone: str = "UTC"
    consent_audio_analysis: bool = False
    consent_data_storage: bool = False
    consent_llm_processing: bool = False


class PatientLLMConsentUpdateRequest(BaseModel):
    consent_llm_processing: bool
