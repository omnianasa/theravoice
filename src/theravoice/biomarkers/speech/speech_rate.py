"""Speech rate: words per minute of speaking duration.

If transcript timestamps needed to establish speaking duration are
unavailable, this returns None (unavailable) rather than inventing timing.
"""

from __future__ import annotations


def speech_rate_wpm(word_count: int, speaking_duration_seconds: float | None) -> float | None:
    if speaking_duration_seconds is None or speaking_duration_seconds <= 0:
        return None
    minutes = speaking_duration_seconds / 60.0
    return word_count / minutes if minutes > 0 else None
