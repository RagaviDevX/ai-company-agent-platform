from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Company"
    env: str = "development"
    backend_url: str = "http://127.0.0.1:8000"
    default_user_id: int = 1

    groq_api_key: str = ""
    openrouter_api_key: str = ""
    huggingface_api_key: str = ""
    tavily_api_key: str = ""

    sqlite_db: str = str(ROOT / "database" / "memory.db")
    qdrant_path: str = str(ROOT / "qdrant_data")
    qdrant_url: str = ""  # e.g. http://localhost:6333 -- if set, used instead of qdrant_path
    uploads_dir: str = str(ROOT / "uploads")
    logs_dir: str = str(ROOT / "logs")
    prompts_dir: str = str(ROOT / "backend" / "prompts")

    planner_model: str = "openrouter/deepseek/deepseek-chat-v3-0324:free"
    coder_model: str = "groq/qwen/qwen3-32b"
    reasoning_model: str = "groq/llama-3.3-70b-versatile"
    vision_model: str = "groq/meta-llama/llama-4-scout-17b-16e-instruct"
    whisper_model: str = "whisper-large-v3"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    collection_name: str = "ai_company_docs"
    max_upload_mb: int = 25


settings = Settings()
