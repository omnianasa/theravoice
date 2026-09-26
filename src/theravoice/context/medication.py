"""Medication context: proximity of an observation to a scheduled medication time.

This module NEVER concludes that medication has "worn off" or caused a
change. It only reports temporal proximity as a contextual fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from theravoice.schemas.medication import MedicationSchedule


@dataclass
class MedicationProximity:
    medication_id: str
    scheduled_time: str
    minutes_from_scheduled: float
    within_window: bool


def _parse_hhmm(value: str) -> time:
    hour_str, minute_str = value.split(":")
    return time(hour=int(hour_str), minute=int(minute_str))


class MedicationContext:
    def __init__(self, window_minutes: int = 90) -> None:
        self._window_minutes = window_minutes

    def find_proximities(
        self, observation_time: datetime, schedules: list[MedicationSchedule]
    ) -> list[MedicationProximity]:
        results: list[MedicationProximity] = []
        for schedule in schedules:
            if schedule.days_of_week and observation_time.weekday() not in schedule.days_of_week:
                continue
            scheduled_time = _parse_hhmm(schedule.scheduled_time)
            scheduled_dt = observation_time.replace(
                hour=scheduled_time.hour,
                minute=scheduled_time.minute,
                second=0,
                microsecond=0,
            )
            delta_minutes = (observation_time - scheduled_dt).total_seconds() / 60.0
            results.append(
                MedicationProximity(
                    medication_id=schedule.medication_id,
                    scheduled_time=schedule.scheduled_time,
                    minutes_from_scheduled=delta_minutes,
                    within_window=abs(delta_minutes) <= self._window_minutes,
                )
            )
        return results
