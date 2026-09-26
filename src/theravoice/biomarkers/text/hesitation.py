"""Text-level hesitation marker detection.

Hesitation markers are configurable per language. Detecting them describes
communication patterns; it is not, and must not be treated as, a diagnostic
signal on its own.
"""

from __future__ import annotations

import re

DEFAULT_ENGLISH_MARKERS = ["um", "uh", "er", "hmm"]
DEFAULT_ARABIC_MARKERS = ["امم", "اه", "يعني", "مم"]


def count_hesitations(text: str, markers: list[str] | None = None) -> int:
    """Count configured hesitation tokens as whole words/tokens in `text`.

    Matching is case-insensitive for Latin scripts and exact for non-Latin
    scripts (Arabic has no case). Word-boundary matching is used to avoid
    matching hesitation markers inside unrelated longer words.
    """
    if not text:
        return 0
    if markers is None:
        markers = DEFAULT_ENGLISH_MARKERS + DEFAULT_ARABIC_MARKERS

    count = 0
    for marker in markers:
        pattern = r"(?<!\w)" + re.escape(marker) + r"(?!\w)"
        count += len(re.findall(pattern, text, flags=re.IGNORECASE | re.UNICODE))
    return count


def hesitation_ratio(text: str, word_count: int, markers: list[str] | None = None) -> float | None:
    """Hesitation markers per word. Returns None if word_count is 0."""
    if word_count <= 0:
        return None
    return count_hesitations(text, markers) / word_count
