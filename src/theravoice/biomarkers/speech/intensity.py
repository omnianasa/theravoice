"""RMS-based vocal intensity biomarkers, reported in descriptive dB terms."""

from __future__ import annotations

import numpy as np


def intensity_metrics(samples: np.ndarray) -> dict[str, float | None]:
    if samples.size == 0:
        return {"rms_db": None, "rms_std_db": None}

    frame_length = 2048
    hop_length = 512
    frames = [
        samples[i : i + frame_length]
        for i in range(0, max(len(samples) - frame_length, 1), hop_length)
    ]
    if not frames:
        frames = [samples]

    rms_values = np.array([np.sqrt(np.mean(np.square(f))) + 1e-12 for f in frames])
    db_values = 20.0 * np.log10(rms_values)

    return {
        "rms_db": float(np.mean(db_values)),
        "rms_std_db": float(np.std(db_values)),
    }
