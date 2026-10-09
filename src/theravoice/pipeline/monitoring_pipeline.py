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
from theravoice.ingestion.bee import (
    BeeAdapter,
    BeeBindingError,
    BeeConnectionError,
    get_bee_adapter,
)
from theravoice.pipeline.analysis_pipeline import (
    AnalysisPipeline,
    AnalysisResult,
    PatientNotFoundError,
)
from theravoice.storage.repositories.bee_sync import BeeSyncRepository
from theravoice.storage.repositories.patient import PatientRepository
from theravoice.storage.repositories.transcript import TranscriptRepository


class MonitoringPipeline:
    def __init__(
        self,
        bee_adapter: BeeAdapter,
        session_factory: sessionmaker,
        source_id: str | None = None,
        bound_patient_id: str | None = None,
    ) -> None:
        self._bee = bee_adapter
        self._session_factory = session_factory
        self._source_id = source_id
        self._bound_patient_id = bound_patient_id
        self._analysis_pipeline = AnalysisPipeline(session_factory=session_factory)

    def poll_patient(self, patient_id: str, since: datetime | None = None) -> list[AnalysisResult]:
        """Pull new transcript segments for a patient and analyze each one.

        Real Bee sources must be explicitly bound to one patient. Stable
        source IDs are used for deduplication; repeated records are skipped
        without excluding records that share a timestamp.
        """
        if self._bee.requires_identity_binding and not (self._source_id and self._bound_patient_id):
            raise BeeBindingError(
                "Real Bee sources require a configured source-to-patient binding."
            )
        if self._bound_patient_id is not None and patient_id != self._bound_patient_id:
            raise BeeBindingError("The configured Bee source is not bound to this patient.")
        if (self._source_id is None) != (self._bound_patient_id is None):
            raise BeeBindingError("Bee source and patient must be configured together.")
        with self._session_factory() as session:
            if PatientRepository(session).get(patient_id) is None:
                raise PatientNotFoundError(f"Patient '{patient_id}' does not exist.")
        if self._source_id is not None:
            try:
                with self._session_factory() as session:
                    BeeSyncRepository(session).begin(self._source_id, patient_id)
            except ValueError as exc:
                raise BeeBindingError(str(exc)) from exc

        try:
            effective_since = since
            if effective_since is None and self._source_id is None:
                with self._session_factory() as session:
                    latest = TranscriptRepository(session).get_latest_timestamp(patient_id)
                effective_since = latest + timedelta(microseconds=1) if latest is not None else None
            segments = self._bee.get_transcript(patient_id, since=effective_since)
        except BeeConnectionError:
            if self._source_id is not None:
                with self._session_factory() as session:
                    BeeSyncRepository(session).mark_failure(self._source_id, "connection_error")
            raise
        results: list[AnalysisResult] = []
        for segment in segments:
            existing_patient_id = None
            if self._source_id is not None:
                with self._session_factory() as session:
                    transcript_repository = TranscriptRepository(session)
                    existing_patient_id = transcript_repository.get_patient_id(segment.id)
            if existing_patient_id is not None and existing_patient_id != patient_id:
                if self._source_id is not None:
                    with self._session_factory() as session:
                        BeeSyncRepository(session).mark_failure(
                            self._source_id, "record_ownership_conflict"
                        )
                raise BeeBindingError(
                    "Bee record identifier is already associated with another patient."
                )
            already_processed = existing_patient_id == patient_id
            if already_processed:
                if self._source_id is not None:
                    with self._session_factory() as session:
                        BeeSyncRepository(session).mark_processed(self._source_id, segment.id)
                continue
            try:
                result = self._analysis_pipeline.run_transcript(
                    patient_id=patient_id,
                    text=segment.text,
                    observation_time=segment.timestamp,
                    transcript_id=segment.id if self._source_id is not None else None,
                )
            except Exception:
                if self._source_id is not None:
                    with self._session_factory() as session:
                        BeeSyncRepository(session).mark_failure(
                            self._source_id, "record_processing_failed"
                        )
                raise
            results.append(result)
            if self._source_id is not None:
                with self._session_factory() as session:
                    BeeSyncRepository(session).mark_processed(self._source_id, segment.id)
        if self._source_id is not None:
            with self._session_factory() as session:
                BeeSyncRepository(session).mark_success(self._source_id)
        return results


def build_monitoring_pipeline(session_factory: sessionmaker) -> MonitoringPipeline:
    """Construct a MonitoringPipeline using the Bee channel from config.

    Reads `bee.mode` ("mock" | "sync" | "proxy") plus the matching
    `bee.sync_dir` / `bee.proxy_base_url` / `bee.proxy_timeout_seconds`
    settings -- see `config/*.yaml` and `docs/bee_integration.md`.
    """
    settings = get_settings()
    source_id = settings.bee.source_id.strip()
    bound_patient_id = settings.bee.patient_id.strip()
    if settings.bee.mode in {"sync", "proxy"} and not (source_id and bound_patient_id):
        raise BeeBindingError(
            "Real Bee sync requires bee.source_id and bee.patient_id to be configured."
        )
    adapter = get_bee_adapter(
        mode=settings.bee.mode,
        sync_dir=settings.bee.sync_dir,
        proxy_base_url=settings.bee.proxy_base_url,
        proxy_timeout_seconds=settings.bee.proxy_timeout_seconds,
        source_id=source_id or "default",
        max_conversations_per_poll=settings.bee.max_conversations_per_poll,
    )
    return MonitoringPipeline(
        bee_adapter=adapter,
        session_factory=session_factory,
        source_id=source_id or None,
        bound_patient_id=bound_patient_id or None,
    )
