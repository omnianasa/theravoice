"""Transcript repository: persistence for raw ingested transcript segments."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from theravoice.schemas.transcript import TranscriptSegment
from theravoice.storage.models import TranscriptSegmentModel


class TranscriptRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, segment: TranscriptSegment) -> TranscriptSegment:
        model = TranscriptSegmentModel(
            id=segment.id,
            patient_id=segment.patient_id,
            text=segment.text,
            start_time=segment.start_time,
            end_time=segment.end_time,
            timestamp=segment.timestamp,
            confidence=segment.confidence,
        )
        self._session.merge(model)
        self._session.flush()
        return segment

    def list_for_patient(self, patient_id: str, limit: int = 200) -> list[TranscriptSegment]:
        stmt = (
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.patient_id == patient_id)
            .order_by(TranscriptSegmentModel.timestamp.desc())
            .limit(limit)
        )
        models = self._session.execute(stmt).scalars().all()
        return [
            TranscriptSegment(
                id=m.id,
                patient_id=m.patient_id,
                text=m.text,
                start_time=m.start_time,
                end_time=m.end_time,
                timestamp=m.timestamp,
                confidence=m.confidence,
            )
            for m in models
        ]

    def get_latest_timestamp(self, patient_id: str) -> datetime | None:
        """Most recent transcript timestamp for a patient, or None if none exist.

        Used by `MonitoringPipeline` as the default incremental cursor when
        polling a Bee adapter, so repeated syncs don't reprocess the same
        conversations.
        """
        stmt = select(func.max(TranscriptSegmentModel.timestamp)).where(
            TranscriptSegmentModel.patient_id == patient_id
        )
        return self._session.execute(stmt).scalar_one_or_none()
