"""Acoustic-level hesitation cues (filled pauses) detected via audio duration.

This module intentionally defers *lexical* hesitation detection (um/uh/etc.)
to `biomarkers.text.hesitation`, which operates on the transcript. This
module only flags unusually long individual pauses as a descriptive acoustic
correlate of hesitation, using the patient's own pause statistics.
"""

from __future__ import annotations

from theravoice.preprocessing.silence import SilenceInterval


def long_pause_count(
    silences: list[SilenceInterval], long_pause_threshold_seconds: float = 1.0
) -> int:
    return sum(1 for s in silences if s.duration_seconds >= long_pause_threshold_seconds)
