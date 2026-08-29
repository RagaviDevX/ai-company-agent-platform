from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from backend.api.schemas import ChatRequest, MemoryRequest, RagRequest, SearchRequest
from backend.config.settings import settings
from backend.graph.workflow import run_company
from backend.memory.store import MemoryStore
from backend.models.llm import chat, chat_vision
from backend.rag.pipeline import RAGPipeline
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

memory = MemoryStore()
rag = RAGPipeline()

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
    }


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if req.mode == "chat":
        text = chat(
            "reasoning",
            [
                {"role": "system", "content": "You are a helpful engineer at AI Company."},
                {"role": "user", "content": req.message},
            ],
        )
        memory.add_conversation(req.user_id, req.message, text)
        return {"final": text, "mode": "chat", "logs": ["Reasoning"]}
    result = run_company(req.message, user_id=req.user_id)
    return result


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
def get_memory(user_id: int = 1):
    return {
        "memories": memory.list_memories(user_id),
        "conversations": memory.list_conversations(user_id),
    }


@app.post("/memory")
def post_memory(req: MemoryRequest):
    mid = memory.add_memory(req.user_id, req.memory)
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
