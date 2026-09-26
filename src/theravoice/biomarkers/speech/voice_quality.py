"""Descriptive acoustic voice-quality features.

These are general-purpose signal-processing features (NOT clinically
validated diagnostic measurements such as jitter/shimmer/HNR computed to
clinical standard). They are useful only as descriptive, longitudinal,
per-patient signals.
"""

from __future__ import annotations

import numpy as np


def voice_quality_metrics(samples: np.ndarray, sample_rate: int) -> dict[str, float | None]:
    try:
        import librosa
    except ImportError:
        return {"zero_crossing_rate": None, "spectral_centroid_hz": None, "spectral_bandwidth_hz": None}

    if samples.size == 0:
        return {"zero_crossing_rate": None, "spectral_centroid_hz": None, "spectral_bandwidth_hz": None}

    zcr = librosa.feature.zero_crossing_rate(samples)
    centroid = librosa.feature.spectral_centroid(y=samples, sr=sample_rate)
    bandwidth = librosa.feature.spectral_bandwidth(y=samples, sr=sample_rate)

    return {
        "zero_crossing_rate": float(np.mean(zcr)),
        "spectral_centroid_hz": float(np.mean(centroid)),
        "spectral_bandwidth_hz": float(np.mean(bandwidth)),
    }
