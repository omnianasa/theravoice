"""Thin ingestion-stage helpers: validation and normalization prior to analysis."""

from __future__ import annotations

from theravoice.ingestion.normalizer import is_empty_text, normalize_text


class ValidationError(ValueError):
    pass


def validate_and_normalize_text(text: str) -> str:
    if text is None:
        raise ValidationError("text is required")
    normalized = normalize_text(text)
    return normalized
