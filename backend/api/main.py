import json
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from backend.api.middleware import RequestContextMiddleware
from backend.api.schemas import ChatRequest, MemoryRequest, RagRequest, SearchRequest, TokenRequest
from backend.auth.dependencies import get_current_user_id
from backend.auth.jwt import create_access_token
from backend.cache.cache import get_cache
from backend.config.settings import settings
from backend.graph.workflow import run_company, run_company_stream
from backend.memory.store import MemoryStore
from backend.models.llm import chat, chat_stream, chat_vision
from backend.rag.pipeline import get_rag_pipeline
from backend.tools.media import image_to_data_url, transcribe_audio
from backend.tools.search import web_search
from backend.utils.logger import read_recent_logs
from backend.utils.paths import ensure_dirs, resolve_upload_path

ensure_dirs()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

memory = MemoryStore()
rag = get_rag_pipeline()  # shared with backend/graph/workflow.py -- see pipeline.py

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


def _check_size(data: bytes) -> None:
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_mb}MB upload limit.",
        )


async def _save_upload(file: UploadFile) -> Path:
    """Read + persist an UploadFile safely, without blocking the event loop.

    Sanitizes the filename (no path traversal), enforces a size limit, and
    writes the bytes in a worker thread rather than on the async event loop.
    """
    data = await file.read()
    _check_size(data)
    try:
        dest = resolve_upload_path(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await run_in_threadpool(dest.write_bytes, data)
    return dest


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "groq": bool(settings.groq_api_key),
        "openrouter": bool(settings.openrouter_api_key),
        "huggingface": bool(settings.huggingface_api_key),
        "cache_backend": get_cache().backend,
        "auth_enabled": settings.auth_enabled,
    }


@app.post("/auth/token")
def issue_token(req: TokenRequest):
    """Issue a bearer token for `req.user_id`.

    This is a stepping stone toward real multi-user auth, not a login
    system: there's no password/credential check yet (the `users` table
    has no credentials column), so anyone who can reach this endpoint can
    mint a token for any user_id. Only enable AUTH_ENABLED once this is
    replaced with, or placed behind, real credential verification -- until
    then it exists so the JWT plumbing (issuing, verifying, and having
    `/chat`/`/memory` trust the token's subject over the request body) can
    be built and tested ahead of that work. Disabled (404) by default.
    """
    if not settings.auth_enabled:
        raise HTTPException(status_code=404, detail="Auth is disabled on this server.")
    return {"access_token": create_access_token(req.user_id), "token_type": "bearer"}


@app.post("/chat")
def chat_endpoint(req: ChatRequest, auth_user_id: int | None = Depends(get_current_user_id)):
    user_id = auth_user_id if auth_user_id is not None else req.user_id
    if req.mode == "chat":
        text = chat(
            "reasoning",
            [
                {"role": "system", "content": "You are a helpful engineer at AI Company."},
                {"role": "user", "content": req.message},
            ],
        )
        memory.add_conversation(user_id, req.message, text)
        return {"final": text, "mode": "chat", "logs": ["Reasoning"]}
    result = run_company(req.message, user_id=user_id)
    return result


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/chat/stream")
def chat_stream_endpoint(req: ChatRequest, auth_user_id: int | None = Depends(get_current_user_id)):
    """Server-Sent Events version of /chat.

    mode="chat" streams text deltas token-by-token as the model generates
    them. mode="company" streams one "agent" event per completed
    LangGraph node (see run_company_stream) so a client gets live
    progress across the full multi-agent run instead of waiting silently
    for the whole pipeline to finish.
    """
    user_id = auth_user_id if auth_user_id is not None else req.user_id

    def event_source():
        if req.mode == "chat":
            parts: list[str] = []
            for delta in chat_stream(
                "reasoning",
                [
                    {"role": "system", "content": "You are a helpful engineer at AI Company."},
                    {"role": "user", "content": req.message},
                ],
            ):
                parts.append(delta)
                yield _sse("delta", {"text": delta})
            final_text = "".join(parts)
            memory.add_conversation(user_id, req.message, final_text)
            yield _sse("done", {"final": final_text, "mode": "chat"})
            return

        for node_name, partial_state in run_company_stream(req.message, user_id=user_id):
            yield _sse("agent", {"agent": node_name, "state": partial_state})
        yield _sse("done", {"mode": "company"})

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    dest = await _save_upload(file)
    suffix = dest.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        memory.add_document(dest.name, "image")
        return {"ok": True, "kind": "image", "path": str(dest)}
    if suffix in {".mp3", ".wav", ".m4a", ".webm", ".ogg"}:
        memory.add_document(dest.name, "audio")
        return {"ok": True, "kind": "audio", "path": str(dest)}
    try:
        info = await run_in_threadpool(rag.ingest_file, str(dest))
        return {"ok": True, "kind": "document", **info}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/memory")
def get_memory(user_id: int = 1, auth_user_id: int | None = Depends(get_current_user_id)):
    user_id = auth_user_id if auth_user_id is not None else user_id
    return {
        "memories": memory.list_memories(user_id),
        "conversations": memory.list_conversations(user_id),
    }


@app.post("/memory")
def post_memory(req: MemoryRequest, auth_user_id: int | None = Depends(get_current_user_id)):
    user_id = auth_user_id if auth_user_id is not None else req.user_id
    mid = memory.add_memory(user_id, req.memory)
    return {"id": mid}


@app.get("/documents")
def documents():
    return {"documents": memory.list_documents()}


@app.get("/logs")
def logs():
    return {"file_logs": read_recent_logs(), "db_logs": memory.list_agent_logs()}


@app.post("/search")
def search(req: SearchRequest):
    return {"results": web_search(req.query, req.max_results)}


@app.post("/vision")
async def vision(prompt: str = Form("Describe this image."), file: UploadFile = File(...)):
    dest = await _save_upload(file)
    data_url = image_to_data_url(str(dest))
    text = await run_in_threadpool(chat_vision, prompt, data_url)
    return {"analysis": text, "filename": dest.name}


@app.post("/voice")
async def voice(file: UploadFile = File(...)):
    dest = await _save_upload(file)
    text = await run_in_threadpool(transcribe_audio, str(dest))
    return {"transcript": text, "filename": dest.name}


@app.post("/rag")
def rag_query(req: RagRequest):
    return {"hits": rag.retrieve(req.query, req.limit)}