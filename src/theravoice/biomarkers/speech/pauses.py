"""Pause biomarkers derived from detected silence intervals."""

from __future__ import annotations

from theravoice.preprocessing.silence import SilenceInterval


def pause_metrics(
    silences: list[SilenceInterval], total_duration_seconds: float
) -> dict[str, float | int]:
    count = len(silences)
    durations = [s.duration_seconds for s in silences]
    total_pause = sum(durations) if durations else 0.0
    mean_pause = (total_pause / count) if count else 0.0
    max_pause = max(durations) if durations else 0.0
    pause_ratio = (total_pause / total_duration_seconds) if total_duration_seconds > 0 else 0.0

    return {
        "pause_count": count,
        "total_pause_duration_seconds": total_pause,
        "mean_pause_duration_seconds": mean_pause,
        "max_pause_duration_seconds": max_pause,
        "pause_ratio": pause_ratio,
    }
