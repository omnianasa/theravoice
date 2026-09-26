"""Daily pipeline: aggregates a patient's day into a DailySummary report."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import sessionmaker

from theravoice.reporting.daily_summary import build_daily_summary


class DailyPipeline:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def run(self, patient_id: str, day: date | None = None):
        day = day or datetime.now(timezone.utc).date()
        with self._session_factory() as session:
            return build_daily_summary(session, patient_id, day)
