import base64
from pathlib import Path

from groq import Groq

from backend.config.settings import settings


def transcribe_audio(file_path: str) -> str:
    if not settings.groq_api_key:
        return "GROQ_API_KEY is missing. Whisper transcription needs Groq."
    client = Groq(api_key=settings.groq_api_key)
    with open(file_path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=(Path(file_path).name, f.read()),
            model=settings.whisper_model,
        )
    return result.text


def image_to_data_url(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}.get(suffix, "jpeg")
    data = base64.b64encode(Path(file_path).read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{data}"
