"""Longer-running monitoring pipeline: pulls new data from a BeeAdapter and
runs the analysis pipeline for each new transcript/audio segment.

This is the integration point for continuous, longitudinal monitoring, as
opposed to the request/response `AnalysisPipeline` used directly by the
transcript/audio ingestion API. `build_monitoring_pipeline()` wires up
whichever real Bee channel (`bee.mode: sync|proxy`) -- or `MockBeeAdapter`,
in `mock` mode -- is configured, so callers (the CLI, the API's
`/bee/sync` route) don't need to know which one is active.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from theravoice.config.settings import get_settings
from theravoice.ingestion.bee import BeeAdapter, get_bee_adapter
from theravoice.pipeline.analysis_pipeline import AnalysisPipeline, AnalysisResult
from theravoice.storage.repositories.transcript import TranscriptRepository


class MonitoringPipeline:
    def __init__(self, bee_adapter: BeeAdapter, session_factory: sessionmaker) -> None:
        self._bee = bee_adapter
        self._session_factory = session_factory
        self._analysis_pipeline = AnalysisPipeline(session_factory=session_factory)

    def _last_synced_at(self, patient_id: str) -> datetime | None:
        """The cursor to pass as `since` on the next poll.

        Every `BeeAdapter.get_transcript` implementation in this project
        treats `since` as inclusive ("at or after"), matching
        `MockBeeAdapter`'s semantics. To avoid reprocessing the most
        recently synced conversation on every subsequent poll, this nudges
        the stored timestamp forward by a microsecond so it becomes an
        effectively-exclusive cursor.
        """
        with self._session_factory() as session:
            latest = TranscriptRepository(session).get_latest_timestamp(patient_id)
        return latest + timedelta(microseconds=1) if latest is not None else None

    def poll_patient(self, patient_id: str, since: datetime | None = None) -> list[AnalysisResult]:
        """Pull new transcript segments for a patient and analyze each one.

        If `since` is not given, defaults to this patient's most recently
        persisted transcript timestamp, so repeated calls (e.g. a "Sync from
        Bee" button) are incremental rather than reprocessing history every
        time.
        """
        effective_since = since if since is not None else self._last_synced_at(patient_id)
        segments = self._bee.get_transcript(patient_id, since=effective_since)
        results: list[AnalysisResult] = []
        for segment in segments:
            result = self._analysis_pipeline.run_transcript(
                patient_id=patient_id, text=segment.text, observation_time=segment.timestamp
            )
            results.append(result)
        return results


def build_monitoring_pipeline(session_factory: sessionmaker) -> MonitoringPipeline:
    """Construct a MonitoringPipeline using the Bee channel from config.

    Reads `bee.mode` ("mock" | "sync" | "proxy") plus the matching
    `bee.sync_dir` / `bee.proxy_base_url` / `bee.proxy_timeout_seconds`
    settings -- see `config/*.yaml` and `docs/bee_integration.md`.
    """
    settings = get_settings()
    adapter = get_bee_adapter(
        mode=settings.bee.mode,
        sync_dir=settings.bee.sync_dir,
        proxy_base_url=settings.bee.proxy_base_url,
        proxy_timeout_seconds=settings.bee.proxy_timeout_seconds,
    )
    return MonitoringPipeline(bee_adapter=adapter, session_factory=session_factory)
