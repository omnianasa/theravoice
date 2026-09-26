"""Silence/pause detection from audio, used by speech pause biomarkers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SilenceInterval:
    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def detect_silence_intervals(
    samples: np.ndarray,
    sample_rate: int,
    top_db: float = 30.0,
    min_silence_seconds: float = 0.15,
) -> list[SilenceInterval]:
    """Detect silence intervals using librosa's non-silent-interval detector.

    Returns silence intervals (the gaps between non-silent intervals), which
    is what pause-based biomarkers need.
    """
    if samples.size == 0:
        return []

    try:
        import librosa
    except ImportError:
        return []

    non_silent = librosa.effects.split(samples, top_db=top_db)
    if len(non_silent) == 0:
        total_seconds = len(samples) / sample_rate
        return [SilenceInterval(0.0, total_seconds)]

    intervals: list[SilenceInterval] = []
    prev_end = 0
    for start, end in non_silent:
        if start > prev_end:
            gap_seconds = (start - prev_end) / sample_rate
            if gap_seconds >= min_silence_seconds:
                intervals.append(SilenceInterval(prev_end / sample_rate, start / sample_rate))
        prev_end = end

    total_samples = len(samples)
    if prev_end < total_samples:
        gap_seconds = (total_samples - prev_end) / sample_rate
        if gap_seconds >= min_silence_seconds:
            intervals.append(SilenceInterval(prev_end / sample_rate, total_samples / sample_rate))

    return intervals
