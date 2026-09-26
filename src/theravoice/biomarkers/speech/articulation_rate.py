"""Articulation rate: words per minute of articulation time (speech minus pauses)."""

from __future__ import annotations


def articulation_rate_wpm(
    word_count: int, total_speech_duration_seconds: float | None, pause_duration_seconds: float
) -> float | None:
    if total_speech_duration_seconds is None:
        return None
    articulation_time = total_speech_duration_seconds - pause_duration_seconds
    if articulation_time <= 0:
        return None
    minutes = articulation_time / 60.0
    return word_count / minutes if minutes > 0 else None
