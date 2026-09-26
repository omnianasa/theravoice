"""Privacy utilities: consent checks and (optional) transcript redaction."""

from __future__ import annotations

import re

from theravoice.config.settings import get_settings

_POTENTIAL_PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-like
    re.compile(r"\b\d{10,}\b"),  # long digit runs (phone-like)
]


class ConsentError(Exception):
    pass


def require_storage_consent(consent_data_storage: bool) -> None:
    settings = get_settings()
    if settings.privacy.require_data_storage_consent and not consent_data_storage:
        raise ConsentError("Patient has not granted data storage consent.")


def require_audio_consent(consent_audio_analysis: bool) -> None:
    settings = get_settings()
    if settings.privacy.require_audio_consent and not consent_audio_analysis:
        raise ConsentError("Patient has not granted audio analysis consent.")


def redact_transcript(text: str) -> str:
    """Lightweight, best-effort redaction of obvious identifier-like substrings.

    This is NOT a substitute for a proper PII-detection pipeline; it exists
    to reduce accidental leakage of obviously sensitive numeric identifiers
    when `privacy.redact_transcripts` is enabled.
    """
    settings = get_settings()
    if not settings.privacy.redact_transcripts:
        return text
    redacted = text
    for pattern in _POTENTIAL_PII_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
