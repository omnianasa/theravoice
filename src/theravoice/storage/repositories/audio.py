"""Audio segment repository.

Respects `privacy.store_raw_audio`: only a `path` reference (or None) and
descriptive metadata are ever persisted here -- raw audio bytes are never
written to the database by this repository.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from theravoice.schemas.audio import AudioSegment
from theravoice.storage.models import AudioSegmentModel


class AudioRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, segment: AudioSegment) -> AudioSegment:
        model = AudioSegmentModel(
            id=segment.id,
            patient_id=segment.patient_id,
            path=segment.path,
            sample_rate=segment.sample_rate,
            duration_seconds=segment.duration_seconds,
            timestamp=segment.timestamp,
            source=segment.source,
        )
        self._session.merge(model)
        self._session.flush()
        return segment

    def list_for_patient(self, patient_id: str, limit: int = 200) -> list[AudioSegment]:
        stmt = (
            select(AudioSegmentModel)
            .where(AudioSegmentModel.patient_id == patient_id)
            .order_by(AudioSegmentModel.timestamp.desc())
            .limit(limit)
        )
        models = self._session.execute(stmt).scalars().all()
        return [
            AudioSegment(
                id=m.id,
                patient_id=m.patient_id,
                path=m.path,
                sample_rate=m.sample_rate,
                duration_seconds=m.duration_seconds,
                timestamp=m.timestamp,
                source=m.source,
            )
            for m in models
        ]
