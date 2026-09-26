#!/usr/bin/env python3
"""Example: run a transcript through the full analysis pipeline directly
(without going through the HTTP API).

Usage:
    python examples/analyze_transcript_example.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from theravoice.pipeline.analysis_pipeline import AnalysisPipeline
from theravoice.schemas.patient import Patient
from theravoice.storage.database import get_session_factory, init_db
from theravoice.storage.repositories.patient import PatientRepository


def main() -> None:
    init_db()
    session_factory = get_session_factory()

    with session_factory() as session:
        repo = PatientRepository(session)
        if not repo.exists("patient-demo-001"):
            repo.create(
                Patient(
                    id="patient-demo-001",
                    display_name="Demo Patient",
                    consent_audio_analysis=True,
                    consent_data_storage=True,
                )
            )
            session.commit()

    pipeline = AnalysisPipeline(session_factory=session_factory)
    result = pipeline.run_transcript(
        patient_id="patient-demo-001",
        text="Good morning, I am feeling okay today.",
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
