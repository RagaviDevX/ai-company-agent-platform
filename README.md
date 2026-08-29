# AI Company — Multi-Model Agentic AI Platform

Production-style multi-agent studio: specialized free models collaborate on software, research, documents, and automation.

No OpenAI. No Anthropic. No Gemini. LiteLLM routes Groq, OpenRouter, and Hugging Face.

## Features

- Multi-agent LangGraph workflow (planner, research, architect, database, coder, QA, reviewer, memory)
- Multi-model routing via LiteLLM
- RAG over PDF / DOCX / TXT / CSV
- SQLite memory + local Qdrant vectors
- Vision (Groq) and Whisper speech-to-text
- DuckDuckGo search
- FastAPI + Streamlit dashboard

## Models

| Task | Model | Provider |
|---|---|---|
| Planner | DeepSeek V3 (free) | OpenRouter |
| Coding | Qwen 3 32B | Groq |
| Reasoning | Llama 3.3 70B | Groq |
| Vision | Llama 4 Scout | Groq |
| Speech | Whisper Large v3 | Groq |
| Embeddings | BGE Small v1.5 | Hugging Face (local) |

If a Groq model id changes, edit `backend/config/settings.py`.

## Setup

```bash
cd AI-COMPANY-AGENT
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add keys to `.env` from Groq, OpenRouter, and optionally Hugging Face.

## Run

Terminal 1: `python run_backend.py`

Swagger: http://127.0.0.1:8000/docs

Terminal 2: `streamlit run frontend/app.py`

Optional: `docker compose up -d` for a Qdrant server. The app already uses on-disk Qdrant under `qdrant_data/`.

## API

- POST /chat — mode=company (full crew) or mode=chat
- POST /upload — ingest files
- GET /memory GET /documents GET /logs
- POST /search POST /vision POST /voice POST /rag

## Tests

```bash
pytest tests -q
```

## Deploy (Render)

- Web service: uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
- Set env vars from .env.example
- Streamlit second service: streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
