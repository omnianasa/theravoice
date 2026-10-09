"""Persistence for Bee source ownership and resumable sync status."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from theravoice.storage.models import BeeSyncStateModel


class BeeSyncRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, source_id: str) -> BeeSyncStateModel | None:
        return self._session.get(BeeSyncStateModel, source_id)

    def begin(self, source_id: str, patient_id: str) -> None:
        state = self.get(source_id)
        if state is not None and state.patient_id != patient_id:
            raise ValueError("Configured Bee source is already bound to another patient.")
        if state is None:
            state = BeeSyncStateModel(source_id=source_id, patient_id=patient_id)
            self._session.add(state)
        state.status = "in_progress"
        state.last_attempt_at = datetime.now(timezone.utc)
        state.error_code = None
        self._session.commit()

    def mark_processed(self, source_id: str, record_id: str) -> None:
        state = self.get(source_id)
        if state is None:
            raise RuntimeError("Bee sync state was not initialized.")
        state.last_processed_record_id = record_id
        self._session.commit()

    def mark_failure(self, source_id: str, error_code: str) -> None:
        state = self.get(source_id)
        if state is None:
            raise RuntimeError("Bee sync state was not initialized.")
        state.status = "failed"
        state.error_code = error_code
        self._session.commit()

    def mark_success(self, source_id: str) -> None:
        state = self.get(source_id)
        if state is None:
            raise RuntimeError("Bee sync state was not initialized.")
        state.status = "success"
        state.last_successful_sync_at = datetime.now(timezone.utc)
        state.error_code = None
        self._session.commit()

    def status(self, source_id: str) -> BeeSyncStateModel | None:
        return self.get(source_id)
