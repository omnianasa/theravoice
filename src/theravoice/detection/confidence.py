"""Confidence estimation for a detected change, based on sample size."""

from __future__ import annotations

import math


class ConfidenceEstimator:
    """Very simple, monotonically-increasing confidence in [0, 1] based on n.

    This is a heuristic, descriptive confidence score -- not a statistical
    p-value or clinical confidence interval.
    """

    def estimate(self, n: int, minimum_observations: int) -> float:
        if n < minimum_observations:
            return 0.0
        # Saturating curve: quickly rises then flattens.
        return min(1.0, 1.0 - math.exp(-(n - minimum_observations + 1) / 10.0))
