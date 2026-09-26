"""Medication repository: medications, schedules, adherence events."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from theravoice.schemas.medication import Medication, MedicationEvent, MedicationSchedule
from theravoice.storage.models import (
    MedicationEventModel,
    MedicationModel,
    MedicationScheduleModel,
)


class MedicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_medication(self, medication: Medication) -> Medication:
        model = MedicationModel(
            id=medication.id,
            patient_id=medication.patient_id,
            name=medication.name,
            dosage=medication.dosage,
            unit=medication.unit,
            active=medication.active,
        )
        self._session.merge(model)
        self._session.flush()
        return medication

    def add_schedule(self, schedule: MedicationSchedule) -> MedicationSchedule:
        model = MedicationScheduleModel(
            medication_id=schedule.medication_id,
            scheduled_time=schedule.scheduled_time,
            timezone=schedule.timezone,
            days_of_week=schedule.days_of_week,
        )
        self._session.add(model)
        self._session.flush()
        return schedule

    def list_schedules_for_patient(self, patient_id: str) -> list[MedicationSchedule]:
        stmt = (
            select(MedicationScheduleModel, MedicationModel)
            .join(MedicationModel, MedicationScheduleModel.medication_id == MedicationModel.id)
            .where(MedicationModel.patient_id == patient_id, MedicationModel.active.is_(True))
        )
        rows = self._session.execute(stmt).all()
        return [
            MedicationSchedule(
                medication_id=s.medication_id,
                scheduled_time=s.scheduled_time,
                timezone=s.timezone,
                days_of_week=s.days_of_week or [],
            )
            for s, _ in rows
        ]

    def log_event(self, event: MedicationEvent) -> MedicationEvent:
        model = MedicationEventModel(
            id=event.id,
            patient_id=event.patient_id,
            medication_id=event.medication_id,
            taken_at=event.taken_at,
            status=event.status,
        )
        self._session.merge(model)
        self._session.flush()
        return event

    def list_events(self, patient_id: str) -> list[MedicationEvent]:
        stmt = select(MedicationEventModel).where(MedicationEventModel.patient_id == patient_id)
        models = self._session.execute(stmt).scalars().all()
        return [
            MedicationEvent(
                id=m.id,
                patient_id=m.patient_id,
                medication_id=m.medication_id,
                taken_at=m.taken_at,
                status=m.status,
            )
            for m in models
        ]
