"""Password hashing and opaque bearer-session helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from theravoice.storage.models import UserModel
from theravoice.storage.repositories.user import UserRepository

PASSWORD_SCRYPT_N = 2**14
PASSWORD_SCRYPT_R = 8
PASSWORD_SCRYPT_P = 1
PASSWORD_HASH_BYTES = 64
SESSION_LIFETIME = timedelta(hours=12)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_SCRYPT_N,
        r=PASSWORD_SCRYPT_R,
        p=PASSWORD_SCRYPT_P,
        dklen=PASSWORD_HASH_BYTES,
    )
    return f"scrypt${PASSWORD_SCRYPT_N}${PASSWORD_SCRYPT_R}${PASSWORD_SCRYPT_P}${salt.hex()}${password_hash.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected_hex = encoded_hash.split("$", 5)
        if algorithm != "scrypt":
            return False
        expected = bytes.fromhex(expected_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError, OverflowError):
        return False
    return hmac.compare_digest(actual, expected)


def issue_session(session: Session, user: UserModel) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + SESSION_LIFETIME
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    UserRepository(session).create_session(
        token_hash=token_hash, user_id=user.id, expires_at=expires_at
    )
    return token, expires_at


def authenticate_session(session: Session, token: str) -> UserModel | None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return UserRepository(session).get_session_user(token_hash, datetime.now(UTC))


def revoke_session(session: Session, token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    UserRepository(session).revoke_session(token_hash)