import httpx
import streamlit as st

BACKEND = "http://127.0.0.1:8000"


def api() -> str:
    return st.session_state.get("backend_url", BACKEND)


def get_json(path: str, **params):
    try:
        r = httpx.get(f"{api()}{path}", params=params, timeout=120)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"Backend not reachable at {api()}{path}. Start FastAPI first. ({exc})")
        return None


def post_json(path: str, payload: dict, timeout: int = 600):
    try:
        r = httpx.post(f"{api()}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


def post_file(path: str, file_name: str, data: bytes, extra: dict | None = None):
    files = {"file": (file_name, data)}
    try:
        r = httpx.post(f"{api()}{path}", files=files, data=extra or {}, timeout=300)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"Upload failed: {exc}")
        return None
