"""Basic audio preprocessing: trimming, normalization of amplitude."""

from __future__ import annotations

import numpy as np


def normalize_amplitude(samples: np.ndarray) -> np.ndarray:
    """Peak-normalize samples to [-1, 1]. Returns input unchanged if silent."""
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak == 0.0:
        return samples
    return samples / peak


def trim_leading_trailing_silence(
    samples: np.ndarray, sample_rate: int, top_db: float = 30.0
) -> np.ndarray:
    """Trim leading/trailing silence using librosa's energy-based trimmer."""
    try:
        import librosa
    except ImportError:
        return samples
    trimmed, _ = librosa.effects.trim(samples, top_db=top_db)
    return trimmed
