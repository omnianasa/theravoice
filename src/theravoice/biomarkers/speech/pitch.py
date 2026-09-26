"""Fundamental frequency (F0 / pitch) biomarkers via librosa's pYIN estimator."""

from __future__ import annotations

import numpy as np


def pitch_metrics(
    samples: np.ndarray, sample_rate: int, fmin: float = 65.0, fmax: float = 400.0
) -> dict[str, float | None]:
    """Compute descriptive F0 statistics. Returns None values if audio too short."""
    try:
        import librosa
    except ImportError:
        return {
            "f0_mean_hz": None,
            "f0_std_hz": None,
            "f0_range_hz": None,
            "voiced_frame_ratio": None,
        }

    if samples.size < sample_rate * 0.05:  # less than 50ms, too short to analyze
        return {
            "f0_mean_hz": None,
            "f0_std_hz": None,
            "f0_range_hz": None,
            "voiced_frame_ratio": None,
        }

    f0, voiced_flag, _ = librosa.pyin(
        samples, fmin=fmin, fmax=fmax, sr=sample_rate
    )
    voiced_f0 = f0[voiced_flag] if voiced_flag is not None else np.array([])
    voiced_f0 = voiced_f0[~np.isnan(voiced_f0)]

    if voiced_f0.size == 0:
        voiced_ratio = float(np.mean(voiced_flag)) if voiced_flag is not None and voiced_flag.size else 0.0
        return {
            "f0_mean_hz": None,
            "f0_std_hz": None,
            "f0_range_hz": None,
            "voiced_frame_ratio": voiced_ratio,
        }

    return {
        "f0_mean_hz": float(np.mean(voiced_f0)),
        "f0_std_hz": float(np.std(voiced_f0)),
        "f0_range_hz": float(np.max(voiced_f0) - np.min(voiced_f0)),
        "voiced_frame_ratio": float(np.mean(voiced_flag)) if voiced_flag is not None else None,
    }
