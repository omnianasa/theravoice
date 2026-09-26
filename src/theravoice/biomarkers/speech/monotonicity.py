"""Pitch-variation-based monotonicity descriptors."""

from __future__ import annotations


def monotonicity_metrics(
    f0_mean_hz: float | None, f0_std_hz: float | None, f0_range_hz: float | None
) -> dict[str, float | None]:
    coefficient_of_variation = None
    if f0_mean_hz and f0_std_hz is not None and f0_mean_hz > 0:
        coefficient_of_variation = f0_std_hz / f0_mean_hz

    return {
        "pitch_std_hz": f0_std_hz,
        "pitch_range_hz": f0_range_hz,
        "pitch_coefficient_of_variation": coefficient_of_variation,
    }
