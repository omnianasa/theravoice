"""Public account registration and bearer-session endpoints."""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from theravoice.api.dependencies import DB_SESSION
from theravoice.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from theravoice.security.user_auth import (
    authenticate_session,
    hash_password,
    issue_session,
    revoke_session,
    verify_password,
)
from theravoice.storage.repositories.user import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(24))


def _auth_response(db: Session, user) -> AuthResponse:
    token, expires_at = issue_session(db, user)
    return AuthResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserResponse(id=user.id, email=user.email, display_name=user.display_name),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = DB_SESSION) -> AuthResponse:
    users = UserRepository(db)
    if users.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    try:
        user = users.create(
            user_id=str(uuid.uuid4()),
            email=payload.email,
            display_name=payload.display_name.strip(),
            password_hash=hash_password(payload.password),
        )
    except IntegrityError as error:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from error
    return _auth_response(db, user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = DB_SESSION) -> AuthResponse:
    user = UserRepository(db).get_by_email(payload.email)
    stored_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    if not verify_password(payload.password, stored_hash) or user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _auth_response(db, user)


@router.get("/me", response_model=UserResponse)
def current_user(
    authorization: str | None = Header(default=None), db: Session = DB_SESSION
) -> UserResponse:
    user = _user_from_authorization(db, authorization)
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    authorization: str | None = Header(default=None), db: Session = DB_SESSION
) -> None:
    _user_from_authorization(db, authorization)
    _, token = authorization.split(" ", 1)
    revoke_session(db, token)


def _user_from_authorization(db: Session, authorization: str | None):
    if authorization is None:
        raise HTTPException(status_code=401, detail="A bearer token is required.")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token:
        raise HTTPException(status_code=401, detail="A valid bearer token is required.")
    user = authenticate_session(db, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Session is invalid or expired.")
    return user