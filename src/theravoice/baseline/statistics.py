"""Rolling statistics helpers used to build a personal baseline."""

from __future__ import annotations

import math


def rolling_mean_std(values: list[float]) -> tuple[float, float, int]:
    """Return (mean, population_std, n) for a list of numeric values."""
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(variance)
    return mean, std, n


def recent_trend(values: list[float], window: int = 5) -> float | None:
    """A simple trend indicator: mean(last `window`) - mean(prior values).

    Returns None if there isn't enough history to compute a meaningful trend.
    """
    if len(values) < window + 1:
        return None
    recent = values[-window:]
    prior = values[:-window]
    if not prior:
        return None
    return (sum(recent) / len(recent)) - (sum(prior) / len(prior))
