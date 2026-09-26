"""Temporal context: time-of-day / recency information."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TemporalContext:
    timestamp: datetime
    hour_of_day: int
    day_of_week: int  # 0=Monday

    @classmethod
    def from_timestamp(cls, timestamp: datetime) -> "TemporalContext":
        return cls(
            timestamp=timestamp,
            hour_of_day=timestamp.hour,
            day_of_week=timestamp.weekday(),
        )
