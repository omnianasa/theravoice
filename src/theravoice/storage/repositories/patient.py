"""Patient repository: abstracts DB access for Patient records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from theravoice.schemas.patient import Patient
from theravoice.storage.models import PatientModel


class PatientRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, patient: Patient) -> Patient:
        model = PatientModel(
            id=patient.id,
            display_name=patient.display_name,
            timezone=patient.timezone,
            consent_audio_analysis=patient.consent_audio_analysis,
            consent_data_storage=patient.consent_data_storage,
            created_at=patient.created_at,
        )
        self._session.merge(model)
        self._session.flush()
        return patient

    def get(self, patient_id: str) -> Patient | None:
        model = self._session.get(PatientModel, patient_id)
        if model is None:
            return None
        return Patient(
            id=model.id,
            display_name=model.display_name,
            timezone=model.timezone,
            consent_audio_analysis=model.consent_audio_analysis,
            consent_data_storage=model.consent_data_storage,
            created_at=model.created_at,
        )

    def exists(self, patient_id: str) -> bool:
        return self._session.get(PatientModel, patient_id) is not None

    def list_all(self) -> list[Patient]:
        models = self._session.execute(select(PatientModel)).scalars().all()
        return [
            Patient(
                id=m.id,
                display_name=m.display_name,
                timezone=m.timezone,
                consent_audio_analysis=m.consent_audio_analysis,
                consent_data_storage=m.consent_data_storage,
                created_at=m.created_at,
            )
            for m in models
        ]
