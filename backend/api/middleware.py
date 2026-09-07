"""Request-scoped observability middleware."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.utils.logger import write_log
from backend.utils.request_context import get_request_id, new_request_id, set_request_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID to every request and logs a structured access line.

    - Accepts an inbound `X-Request-ID` header (so a caller/gateway that
      already generates one gets it echoed back and correlated), or
      generates a new one.
    - Stores it in a contextvar for the lifetime of the request (see
      backend/utils/request_context.py) so every write_log() call during
      that request -- agent calls, cache misses, errors -- is tagged with
      the same ID.
    - Returns it via the `X-Request-ID` response header for client-side
      correlation (support tickets, browser dev tools, etc.).
    - Logs one structured access line per request with method/path/status/
      duration, including on unhandled exceptions.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or new_request_id()
        set_request_id(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            write_log(
                {
                    "event": "request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                }
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = get_request_id()
        write_log(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        return response