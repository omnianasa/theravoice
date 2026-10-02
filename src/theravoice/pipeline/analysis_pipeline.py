"""The core analysis pipeline.

Receive transcript/audio
        -> Validate patient (+ consent)
        -> Normalize
        -> Store raw segment
        -> Extract biomarkers
        -> Update / inspect personal baseline
        -> Run change detection
        -> Run context engine (inside orchestrator)
        -> Run multi-agent orchestrator
        -> Persist biomarkers / events / actions
        -> Return structured analysis result

This module is intentionally the single place all of the above is wired
together, so `POST /ingestion/transcript` and `POST /ingestion/audio` are
thin adapters over it. `run_transcript` and `run_audio` share the
baseline/detection/orchestration/persistence logic via `_analyze_snapshot`
so both entry points behave identically from that point onward.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from theravoice.agents.orchestrator import AgentOrchestrator
from theravoice.agents.summary_agent import SummaryAgent
from theravoice.baseline.personal import compute_baseline
from theravoice.baseline.profile import PatientProfile
from theravoice.baseline.updater import BaselineUpdater
from theravoice.biomarkers.extractor import BiomarkerExtractor
from theravoice.config.settings import get_settings
from theravoice.detection.anomaly_detector import AnomalyDetector
from theravoice.detection.change_detector import ChangeDetector
from theravoice.detection.confidence import ConfidenceEstimator
from theravoice.detection.thresholds import ThresholdManager
from theravoice.ingestion.normalizer import is_empty_text, normalize_text
from theravoice.llm.client import create_llm_client
from theravoice.schemas.action import Action
from theravoice.schemas.audio import AudioSegment
from theravoice.schemas.biomarker import BiomarkerSnapshot
from theravoice.schemas.event import Event
from theravoice.schemas.patient import Patient
from theravoice.schemas.transcript import TranscriptSegment
from theravoice.security.privacy import (
    redact_transcript,
    require_audio_consent,
    require_storage_consent,
)
from theravoice.storage.repositories.audio import AudioRepository
from theravoice.storage.repositories.biomarker import BiomarkerRepository
from theravoice.storage.repositories.event import EventRepository
from theravoice.storage.repositories.medication import MedicationRepository
from theravoice.storage.repositories.patient import PatientRepository
from theravoice.storage.repositories.transcript import TranscriptRepository


class AnalysisResult(BaseModel):
    """Structured response returned by the analysis pipeline."""

    patient_id: str
    text_length: int = 0
    biomarkers: dict[str, float | None] = Field(default_factory=dict)
    baseline_status: str = "insufficient_data"
    baseline: dict[str, dict[str, float]] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    status: str = "processed"


class PatientNotFoundError(Exception):
    pass


class AnalysisPipeline:
    """Orchestrates the full transcript/audio -> structured result flow."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory
        settings = get_settings()
        self._settings = settings

        self._extractor = BiomarkerExtractor(
            hesitation_markers=settings.hesitation.english + settings.hesitation.arabic
        )
        self._baseline_updater = BaselineUpdater(
            rolling_window_size=settings.baseline.rolling_window_size,
            update_enabled=settings.baseline.update_enabled,
        )
        self._anomaly_detector = AnomalyDetector(
            threshold_manager=ThresholdManager(
                warning_z=settings.detection.warning_z,
                significant_z=settings.detection.significant_z,
            ),
            confidence_estimator=ConfidenceEstimator(),
            minimum_observations=settings.baseline.minimum_observations,
        )
        self._change_detector = ChangeDetector(self._anomaly_detector)
        self._orchestrator = AgentOrchestrator(
            summary_agent=SummaryAgent(llm_client=create_llm_client(settings.llm))
        )

    # ---- shared helpers ---------------------------------------------------
    def _get_patient_or_raise(self, session: Session, patient_id: str) -> Patient:
        patient = PatientRepository(session).get(patient_id)
        if patient is None:
            raise PatientNotFoundError(f"Patient '{patient_id}' does not exist.")
        return patient

    def _load_profile(self, biomarker_repo: BiomarkerRepository, patient_id: str) -> PatientProfile:
        """Rebuild an in-memory rolling profile from persisted history."""
        profile = PatientProfile(patient_id=patient_id)
        # Discover which metrics we have history for by pulling recent rows.
        recent_values = biomarker_repo.get_all(patient_id, limit=1000)
        metric_names = {v.name for v in recent_values if v.available}
        for name in metric_names:
            history = biomarker_repo.get_history(
                patient_id, name, limit=self._settings.baseline.rolling_window_size
            )
            for value in history:
                profile.record(name, value, self._settings.baseline.rolling_window_size)
        return profile

    def _analyze_snapshot(
        self,
        session: Session,
        patient_id: str,
        snapshot: BiomarkerSnapshot,
        observation_time: datetime,
        text_length: int,
        allow_llm_summary: bool = False,
    ) -> AnalysisResult:
        """Baseline -> detection -> context -> orchestrator -> persistence.

        Shared by `run_transcript` and `run_audio` once each has produced a
        `BiomarkerSnapshot` for the current observation.
        """
        biomarker_repo = BiomarkerRepository(session)
        event_repo = EventRepository(session)
        medication_repo = MedicationRepository(session)

        # 1. Load rolling profile + compute current baseline BEFORE updating
        #    with this observation (so we compare against prior history).
        profile = self._load_profile(biomarker_repo, patient_id)
        baseline, status_by_metric = compute_baseline(
            profile, self._settings.baseline.minimum_observations
        )
        overall_status = (
            "ok" if any(s == "ok" for s in status_by_metric.values()) else "insufficient_data"
        )

        # 2. Run change detection against that baseline.
        anomaly_results = (
            self._change_detector.detect(snapshot, baseline) if overall_status == "ok" else []
        )

        # 3. Persist this observation's biomarkers (updates history for
        #    future baselines) and the freshly-computed baseline snapshot.
        biomarker_repo.save_snapshot(snapshot)
        if baseline.metrics:
            biomarker_repo.save_baseline(baseline)

        # 4. Run multi-agent orchestrator (includes context engine).
        medication_schedules = medication_repo.list_schedules_for_patient(patient_id)
        orchestrator_response = self._orchestrator.run(
            patient_id=patient_id,
            anomaly_results=anomaly_results,
            medication_schedules=medication_schedules,
            observation_time=observation_time,
            allow_llm_summary=allow_llm_summary,
        )

        # 5. Persist events produced with real evidence only.
        for event in orchestrator_response.events:
            event_repo.save(event)

        return AnalysisResult(
            patient_id=patient_id,
            text_length=text_length,
            biomarkers=snapshot.as_dict(),
            baseline_status=overall_status,
            baseline={
                name: {"mean": stat.mean, "std": stat.std, "n": stat.n}
                for name, stat in baseline.metrics.items()
            },
            events=orchestrator_response.events,
            actions=orchestrator_response.actions,
            context={
                "notes": orchestrator_response.data.get("context_notes", []),
                "summary_text": orchestrator_response.data.get("summary_text", ""),
            },
            status="processed",
        )

    # ---- transcript entry point --------------------------------------------
    def run_transcript(
        self,
        patient_id: str,
        text: str,
        observation_time: datetime | None = None,
    ) -> AnalysisResult:
        """Run the full pipeline for a text transcript observation."""
        observation_time = observation_time or datetime.now(timezone.utc)

        with self._session_factory() as session:
            patient = self._get_patient_or_raise(session, patient_id)
            require_storage_consent(patient.consent_data_storage)

            normalized_text = normalize_text(text)
            text_length = len(normalized_text)

            # Persist the raw transcript segment (redacted if configured).
            segment = TranscriptSegment(
                id=str(uuid.uuid4()),
                patient_id=patient_id,
                text=redact_transcript(normalized_text),
                timestamp=observation_time,
            )
            TranscriptRepository(session).save(segment)

            if is_empty_text(normalized_text):
                snapshot = self._extractor.extract(patient_id, text=normalized_text)
                BiomarkerRepository(session).save_snapshot(snapshot)
                session.commit()
                return AnalysisResult(
                    patient_id=patient_id,
                    text_length=0,
                    biomarkers={},
                    baseline_status="insufficient_data",
                    status="processed_empty_text",
                )

            snapshot: BiomarkerSnapshot = self._extractor.extract(patient_id, text=normalized_text)
            result = self._analyze_snapshot(
                session,
                patient_id,
                snapshot,
                observation_time,
                text_length,
                allow_llm_summary=patient.consent_llm_processing,
            )
            session.commit()
            return result

    # ---- audio entry point -------------------------------------------------
    def run_audio(
        self,
        patient_id: str,
        samples: "object",
        sample_rate: int,
        duration_seconds: float,
        text: str | None = None,
        source: str = "upload",
        observation_time: datetime | None = None,
    ) -> AnalysisResult:
        """Run the full pipeline for an audio observation.

        Args:
            samples: mono float32 numpy array of decoded audio samples.
            sample_rate: sample rate of `samples`, in Hz.
            duration_seconds: total duration of the decoded audio.
            text: optional accompanying transcript (e.g. from ASR or typed
                alongside the recording). When provided, word-count-dependent
                acoustic metrics (speech rate, articulation rate) become
                available; when omitted, those metrics are correctly marked
                unavailable rather than fabricated.
            source: free-form label for where the audio came from
                ("upload", "bee", ...).
        """
        observation_time = observation_time or datetime.now(timezone.utc)

        with self._session_factory() as session:
            patient = self._get_patient_or_raise(session, patient_id)
            require_storage_consent(patient.consent_data_storage)
            require_audio_consent(patient.consent_audio_analysis)

            # Respect privacy.store_raw_audio: never persist a path to raw
            # audio bytes unless the deployment explicitly opts in, and even
            # then this pipeline itself never writes the bytes -- only a
            # caller-supplied path reference, if any, is recorded.
            audio_segment = AudioSegment(
                id=str(uuid.uuid4()),
                patient_id=patient_id,
                path=None,
                sample_rate=sample_rate,
                duration_seconds=duration_seconds,
                timestamp=observation_time,
                source=source,
            )
            AudioRepository(session).save(audio_segment)

            text_length = 0
            word_count: int | None = None
            text_values: list = []
            normalized_text = normalize_text(text) if text else ""

            if not is_empty_text(normalized_text):
                text_length = len(normalized_text)
                TranscriptRepository(session).save(
                    TranscriptSegment(
                        id=str(uuid.uuid4()),
                        patient_id=patient_id,
                        text=redact_transcript(normalized_text),
                        timestamp=observation_time,
                    )
                )
                text_values = self._extractor.extract_text(patient_id, normalized_text)
                word_count_value = next(
                    (v for v in text_values if v.name == "word_count" and v.available), None
                )
                word_count = int(word_count_value.value) if word_count_value else None

            speech_values = self._extractor.extract_speech(
                patient_id, samples, sample_rate, word_count=word_count
            )
            snapshot = BiomarkerSnapshot(
                patient_id=patient_id,
                timestamp=observation_time,
                values=list(text_values) + list(speech_values),
            )

            result = self._analyze_snapshot(
                session,
                patient_id,
                snapshot,
                observation_time,
                text_length,
                allow_llm_summary=patient.consent_llm_processing,
            )
            session.commit()
            return result
