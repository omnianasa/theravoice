"""Lightweight noise-floor estimation.

This is intentionally simple (not a full denoiser): TheraVoice's biomarkers
are meant to be descriptive of the patient's own recordings over time, and
aggressive denoising can distort exactly the acoustic cues we want to track
longitudinally.
"""

from __future__ import annotations

import numpy as np


def estimate_noise_floor_db(samples: np.ndarray, frame_percentile: float = 10.0) -> float:
    """Estimate a rough noise floor in dBFS using the quietest frames.

    Args:
        samples: mono float32 samples in [-1, 1].
        frame_percentile: percentile of frame RMS values treated as "noise".
    """
    if samples.size == 0:
        return float("-inf")

    frame_length = 1024
    hop_length = 512
    frames = [
        samples[i : i + frame_length]
        for i in range(0, max(len(samples) - frame_length, 1), hop_length)
    ]
    if not frames:
        frames = [samples]

    rms_values = np.array([np.sqrt(np.mean(np.square(f))) + 1e-12 for f in frames])
    noise_rms = float(np.percentile(rms_values, frame_percentile))
    return 20.0 * np.log10(noise_rms + 1e-12)
