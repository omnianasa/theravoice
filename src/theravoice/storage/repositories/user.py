"""Persistence helpers for user accounts and revocable login sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from theravoice.storage.models import UserModel, UserSessionModel


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> UserModel | None:
        return self._session.execute(
            select(UserModel).where(UserModel.email == email)
        ).scalar_one_or_none()

    def get_by_id(self, user_id: str) -> UserModel | None:
        return self._session.get(UserModel, user_id)

    def create(
        self, *, user_id: str, email: str, display_name: str, password_hash: str
    ) -> UserModel:
        user = UserModel(
            id=user_id,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def create_session(self, *, token_hash: str, user_id: str, expires_at: datetime) -> None:
        self._session.add(
            UserSessionModel(token_hash=token_hash, user_id=user_id, expires_at=expires_at)
        )
        self._session.flush()

    def get_session_user(self, token_hash: str, now: datetime) -> UserModel | None:
        record = self._session.get(UserSessionModel, token_hash)
        if record is None or record.expires_at <= now:
            if record is not None:
                self._session.delete(record)
                self._session.flush()
            return None
        return self.get_by_id(record.user_id)

    def revoke_session(self, token_hash: str) -> None:
        record = self._session.get(UserSessionModel, token_hash)
        if record is not None:
            self._session.delete(record)
            self._session.flush()