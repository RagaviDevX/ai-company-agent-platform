from pathlib import Path

from backend.config.settings import settings


def ensure_dirs() -> None:
    for p in (
        Path(settings.uploads_dir),
        Path(settings.logs_dir),
        Path(settings.qdrant_path),
        Path(settings.sqlite_db).parent,
    ):
        p.mkdir(parents=True, exist_ok=True)


def load_prompt(name: str) -> str:
    path = Path(settings.prompts_dir) / name
    return path.read_text(encoding="utf-8").strip()
