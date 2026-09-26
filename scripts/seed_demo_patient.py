#!/usr/bin/env python3
"""Seed a demo patient (patient-demo-001) into the local database.

Usage:
    python scripts/seed_demo_patient.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from theravoice.schemas.patient import Patient
from theravoice.storage.database import get_session_factory, init_db
from theravoice.storage.repositories.patient import PatientRepository


def main() -> None:
    init_db()
    session_factory = get_session_factory()
    with session_factory() as session:
        repo = PatientRepository(session)
        if repo.exists("patient-demo-001"):
            print("patient-demo-001 already exists.")
            return
        repo.create(
            Patient(
                id="patient-demo-001",
                display_name="Demo Patient",
                timezone="UTC",
                consent_audio_analysis=True,
                consent_data_storage=True,
            )
        )
        session.commit()
    print("Seeded patient-demo-001.")


if __name__ == "__main__":
    main()
