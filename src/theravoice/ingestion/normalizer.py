"""Normalization utilities applied to raw ingested text/audio metadata.

Normalization here is intentionally conservative: it never fabricates data
(e.g. timestamps) and never silently drops information needed later, such as
whether timing metadata was actually present.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize unicode form and collapse internal whitespace.

    Does not lowercase or strip punctuation, since some biomarkers (sentence
    structure, hesitation tokens) depend on original casing/punctuation.
    """
    if text is None:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def is_empty_text(text: str | None) -> bool:
    return text is None or normalize_text(text) == ""
