"""API-key based authentication. Disabled by default for local development."""

from __future__ import annotations

import hmac

from theravoice.config.settings import get_settings


class AuthenticationError(Exception):
    pass


def verify_api_key(provided_key: str | None) -> bool:
    """Return True if the request is authenticated.

    If `security.require_api_key` is False (local dev default), every
    request is treated as authenticated. In production, a matching
    `X-API-Key` header is required.
    """
    settings = get_settings()
    if not settings.security.require_api_key:
        return True
    if not settings.security.api_key:
        # Misconfiguration: required but no key configured. Fail closed.
        return False
    return provided_key is not None and hmac.compare_digest(
        provided_key, settings.security.api_key
    )
