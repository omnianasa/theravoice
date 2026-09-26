"""Segment audio into voiced (non-silent) regions for biomarker extraction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class VoicedSegment:
    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def segment_voiced_regions(
    samples: np.ndarray, sample_rate: int, top_db: float = 30.0
) -> list[VoicedSegment]:
    """Return non-silent (voiced/speech-containing) regions of the signal."""
    if samples.size == 0:
        return []
    try:
        import librosa
    except ImportError:
        total_seconds = len(samples) / sample_rate
        return [VoicedSegment(0.0, total_seconds)]

    intervals = librosa.effects.split(samples, top_db=top_db)
    return [
        VoicedSegment(start / sample_rate, end / sample_rate) for start, end in intervals
    ]
