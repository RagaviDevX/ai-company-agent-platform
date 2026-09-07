"""Per-request correlation ID, propagated via contextvars.

contextvars propagate automatically across `await` points and into code
run through Starlette's `run_in_threadpool` (which copies the current
context into the worker thread), so a request ID set once in middleware
is visible to every `write_log()` call made while handling that request
-- including deep inside agent/model code -- without threading a
request_id parameter through every function signature.
"""

import contextvars
import uuid

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def set_request_id(value: str) -> None:
    _request_id_var.set(value)


def get_request_id() -> str:
    return _request_id_var.get()