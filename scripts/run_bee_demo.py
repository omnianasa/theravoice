#!/usr/bin/env python3
"""End-to-end demo: real Bee integration -> full TheraVoice pipeline.

This script is the concrete "does something useful for a person" demo:

  1. Seeds a demo patient (if not already present).
  2. Reads conversations via `BeeSyncAdapter` -- the same code path used for
     a real `bee sync` export (see docs/bee_integration.md) -- from the
     bundled sample fixture at data/examples/bee_sync_sample/ (clearly
     labeled there as a hand-authored demo, not real captured data).
  3. Runs every new conversation through the full analysis pipeline
     (biomarkers -> personal baseline -> change detection -> context ->
     multi-agent orchestration -> persistence).
  4. Prints, in plain language, what changed and what the system suggests --
     exactly what a person would see from `theravoice sync-bee` or the
     dashboard's "Sync from Bee" button.

To run this against your OWN real Bee data instead of the bundled sample,
either:
  - set `bee.mode: sync` and `bee.sync_dir: <path to your bee sync output>`
    in config/development.yaml, then run `theravoice sync-bee --patient-id
    <id>`; or
  - run `bee login` && `bee proxy` in another terminal, set `bee.mode: proxy`
    in config, and run the same `theravoice sync-bee` command.

Usage:
    python scripts/run_bee_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from theravoice.ingestion.bee import BeeSyncAdapter  # noqa: E402
from theravoice.pipeline.monitoring_pipeline import MonitoringPipeline  # noqa: E402
from theravoice.schemas.patient import Patient  # noqa: E402
from theravoice.storage.database import get_session_factory, init_db  # noqa: E402
from theravoice.storage.repositories.patient import PatientRepository  # noqa: E402

PATIENT_ID = "patient-demo-001"
SAMPLE_SYNC_DIR = REPO_ROOT / "data" / "examples" / "bee_sync_sample"


def main() -> None:
    init_db()
    session_factory = get_session_factory()

    with session_factory() as session:
        repo = PatientRepository(session)
        if not repo.exists(PATIENT_ID):
            repo.create(
                Patient(
                    id=PATIENT_ID,
                    display_name="Demo Patient",
                    consent_audio_analysis=True,
                    consent_data_storage=True,
                )
            )
            session.commit()

    bee_adapter = BeeSyncAdapter(sync_dir=SAMPLE_SYNC_DIR)
    pipeline = MonitoringPipeline(bee_adapter=bee_adapter, session_factory=session_factory)

    print(f"Pulling Bee conversations for {PATIENT_ID} from {SAMPLE_SYNC_DIR} ...\n")
    results = pipeline.poll_patient(PATIENT_ID)

    if not results:
        print("No new conversations found (already synced, or the fixture is empty).")
        return

    print(f"Processed {len(results)} conversation(s) through the full pipeline:\n")
    for i, result in enumerate(results, start=1):
        print(f"[{i}] status={result.status}  baseline_status={result.baseline_status}")
        if result.biomarkers:
            shown = {k: round(v, 2) for k, v in list(result.biomarkers.items())[:4]}
            print(f"    biomarkers (sample): {shown}")
        for event in result.events:
            print(f"    \u26a0  {event.type} ({event.severity})")
            for evidence in event.evidence:
                print(f"        - {evidence.description}")
        for action in result.actions:
            print(f"    \u2192 [{action.type}] {action.message}")
        if not result.events and not result.actions:
            print("    (no notable deviation from this patient's personal baseline yet)")
        print()

    print("These observations are descriptive and are not a diagnosis.")
    print("\nRun this script again: it's incremental, so a second run will report")
    print('"No new conversations found" since MonitoringPipeline tracks the last')
    print("synced timestamp per patient automatically.")


if __name__ == "__main__":
    main()
