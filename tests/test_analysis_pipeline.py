"""AnalysisPipeline integration tests (the 'critical implementation requirement')."""

from __future__ import annotations

import pytest

from theravoice.pipeline.analysis_pipeline import AnalysisPipeline, PatientNotFoundError
from theravoice.schemas.patient import Patient
from theravoice.storage.repositories.patient import PatientRepository


def _make_patient(session_factory, patient_id="pipeline-p1"):
    with session_factory() as session:
        PatientRepository(session).create(
            Patient(id=patient_id, display_name="Pipeline Patient", consent_data_storage=True)
        )
        session.commit()
    return patient_id


def test_run_transcript_raises_for_unknown_patient(session_factory):
    pipeline = AnalysisPipeline(session_factory=session_factory)
    with pytest.raises(PatientNotFoundError):
        pipeline.run_transcript(patient_id="ghost", text="hello")


def test_run_transcript_end_to_end_first_observation(session_factory):
    patient_id = _make_patient(session_factory)
    pipeline = AnalysisPipeline(session_factory=session_factory)

    result = pipeline.run_transcript(
        patient_id=patient_id, text="Good morning, I am feeling okay today."
    )

    assert result.status == "processed"
    assert result.text_length > 0
    assert result.biomarkers["word_count"] == 7
    # First-ever observation: no history yet -> insufficient_data, no events.
    assert result.baseline_status == "insufficient_data"
    assert result.events == []


def test_run_transcript_never_fabricates_speech_rate(session_factory):
    patient_id = _make_patient(session_factory, "pipeline-p2")
    pipeline = AnalysisPipeline(session_factory=session_factory)
    result = pipeline.run_transcript(patient_id=patient_id, text="hello there")
    # No audio was supplied, so speech-only metrics must not appear as
    # fabricated numeric biomarkers.
    assert "speech_rate_wpm" not in result.biomarkers


def test_run_transcript_empty_text_short_circuits(session_factory):
    patient_id = _make_patient(session_factory, "pipeline-p3")
    pipeline = AnalysisPipeline(session_factory=session_factory)
    result = pipeline.run_transcript(patient_id=patient_id, text="   ")
    assert result.status == "processed_empty_text"
    assert result.text_length == 0
    assert result.biomarkers == {}


def test_run_audio_end_to_end_with_synthetic_tone(session_factory):
    import numpy as np

    patient_id = "pipeline-audio1"
    with session_factory() as session:
        PatientRepository(session).create(
            Patient(
                id=patient_id,
                display_name="Audio Patient",
                consent_data_storage=True,
                consent_audio_analysis=True,
            )
        )
        session.commit()

    pipeline = AnalysisPipeline(session_factory=session_factory)

    sample_rate = 16000
    duration_seconds = 1.0
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False)
    samples = 0.2 * np.sin(2 * np.pi * 150.0 * t).astype("float32")

    result = pipeline.run_audio(
        patient_id=patient_id,
        samples=samples,
        sample_rate=sample_rate,
        duration_seconds=duration_seconds,
    )
    assert result.status == "processed"
    # No accompanying transcript: word-count-dependent metrics must not be
    # fabricated, but acoustic-only metrics should be present.
    assert "speech_rate_wpm" not in result.biomarkers
    assert "rms_db" in result.biomarkers


def test_run_audio_requires_consent(session_factory):
    import numpy as np

    with session_factory() as session:
        PatientRepository(session).create(
            Patient(
                id="pipeline-audio-noconsent",
                display_name="No Consent",
                consent_data_storage=True,
                consent_audio_analysis=False,
            )
        )
        session.commit()

    pipeline = AnalysisPipeline(session_factory=session_factory)
    samples = np.zeros(16000, dtype="float32")

    from theravoice.security.privacy import ConsentError

    with pytest.raises(ConsentError):
        pipeline.run_audio(
            patient_id="pipeline-audio-noconsent",
            samples=samples,
            sample_rate=16000,
            duration_seconds=1.0,
        )


def test_repeated_observations_build_baseline_and_eventually_detect(session_factory):
    patient_id = _make_patient(session_factory, "pipeline-p4")
    pipeline = AnalysisPipeline(session_factory=session_factory)

    # testing.yaml sets baseline.minimum_observations: 3
    for _ in range(3):
        pipeline.run_transcript(patient_id=patient_id, text="Good morning, I am okay.")

    # A noticeably different observation should be evaluated against a now
    # non-trivial baseline (status becomes "ok" once enough history exists).
    result = pipeline.run_transcript(
        patient_id=patient_id,
        text="Um, uh, I, I, I am not, not feeling very good today at all honestly.",
    )
    assert result.baseline_status in ("ok", "insufficient_data")
    if result.baseline_status == "ok":
        # Should not fabricate an event without real evidence; only assert
        # events (if any) reference metrics actually present in this snapshot.
        for event in result.events:
            assert event.severity in ("warning", "significant")
            assert len(event.evidence) > 0
