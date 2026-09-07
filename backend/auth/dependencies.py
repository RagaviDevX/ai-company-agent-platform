from fastapi import Header, HTTPException

from backend.auth.jwt import decode_access_token
from backend.config.settings import settings


async def get_current_user_id(authorization: str | None = Header(default=None)) -> int | None:
    """Resolve the caller's user_id from a bearer token, or None when auth is off.

    When AUTH_ENABLED is false (the default -- the zero-config, single-user
    local flow this app ships with), this is a no-op: it returns None, and
    callers should fall back to whatever `user_id` the request body
    already carries. Existing deployments, clients, and the test suite are
    completely unaffected.

    When AUTH_ENABLED is true, a valid `Authorization: Bearer <jwt>` header
    is required, and its `sub` claim -- not the request body -- is used as
    the user_id, so one authenticated user can never write data as another
    user just by changing a field in their request.
    """
    if not settings.auth_enabled:
        return None
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject.") from exc