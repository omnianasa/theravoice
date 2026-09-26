"""Z-score threshold configuration for change detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThresholdManager:
    warning_z: float = 1.5
    significant_z: float = 2.0

    def classify(self, abs_z: float | None) -> str:
        if abs_z is None:
            return "insufficient_data"
        if abs_z >= self.significant_z:
            return "significant"
        if abs_z >= self.warning_z:
            return "warning"
        return "normal"
