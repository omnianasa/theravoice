"""Baseline updater: incorporates new observations into a patient's profile."""

from __future__ import annotations

from theravoice.baseline.profile import PatientProfile
from theravoice.schemas.biomarker import BiomarkerSnapshot


class BaselineUpdater:
    def __init__(self, rolling_window_size: int, update_enabled: bool = True) -> None:
        self._window_size = rolling_window_size
        self._update_enabled = update_enabled

    def update(self, profile: PatientProfile, snapshot: BiomarkerSnapshot) -> PatientProfile:
        if not self._update_enabled:
            return profile
        for value in snapshot.values:
            if value.available and value.value is not None:
                profile.record(value.name, float(value.value), self._window_size)
        return profile
