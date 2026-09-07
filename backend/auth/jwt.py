"""Minimal JWT issuing/verification for future multi-user support.

There's no password/user-account system yet (the `users` table only has
name/email, no credentials), so this intentionally does not implement a
full login flow. It provides the JWT primitives -- create_access_token /
decode_access_token -- and an opt-in `AUTH_ENABLED` gate (see
backend/config/settings.py and backend/auth/dependencies.py) so the app
can start requiring bearer tokens on a per-deployment basis without a
breaking change today, and without every existing single-user deployment
or the test suite needing to start sending tokens.
"""

from datetime import datetime, timedelta, timezone

import jwt

from backend.config.settings import settings


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured.")
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=expires_minutes or settings.jwt_expires_minutes)
    payload = {"sub": str(user_id), "iat": now, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET is not configured.")
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc