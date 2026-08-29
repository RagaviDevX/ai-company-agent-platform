from typing import Any

import httpx
from groq import Groq

from backend.config.settings import settings
from backend.utils.logger import write_log

MODELS = {
    "planner": settings.planner_model,
    "coder": settings.coder_model,
    "reasoning": settings.reasoning_model,
    "vision": settings.vision_model,
}

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _provider(model: str) -> str:
    if model.startswith("openrouter/"):
        return "openrouter"
    if model.startswith("huggingface/"):
        return "huggingface"
    return "groq"


def _bare_model(model: str) -> str:
    for prefix in ("openrouter/", "groq/", "huggingface/"):
        if model.startswith(prefix):
            return model[len(prefix) :]
    return model


def _api_key_for(model: str) -> str:
    provider = _provider(model)
    if provider == "openrouter":
        return settings.openrouter_api_key
    if provider == "huggingface":
        return settings.huggingface_api_key
    return settings.groq_api_key


def _missing_keys_message(model: str) -> str:
    provider = _provider(model)
    if provider == "openrouter" and not settings.openrouter_api_key:
        return "API keys are not configured. Add OPENROUTER_API_KEY to `.env`."
    if provider == "groq" and not settings.groq_api_key:
        return "API keys are not configured. Add GROQ_API_KEY to `.env`."
    return ""


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _call_groq(model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> str:
    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=_bare_model(model),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _content_text(response.choices[0].message.content)


def _call_openrouter(model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> str:
    payload = {
        "model": _bare_model(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:8000",
        "X-Title": settings.app_name,
    }
    with httpx.Client(timeout=120) as client:
        response = client.post(OPENROUTER_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    return _content_text(data["choices"][0]["message"].get("content"))


def _complete(model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> str:
    provider = _provider(model)
    if provider == "openrouter":
        return _call_openrouter(model, messages, temperature, max_tokens)
    return _call_groq(model, messages, temperature, max_tokens)


def chat(
    role: str,
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    model = MODELS.get(role, settings.reasoning_model)
    missing = _missing_keys_message(model)
    if missing:
        write_log({"agent": role, "model": model, "error": "missing_api_key"})
        return missing

    try:
        text = _complete(model, messages, temperature, max_tokens)
        write_log(
            {
                "agent": role,
                "model": model,
                "input_preview": str(messages[-1].get("content", ""))[:400],
                "output_preview": text[:400],
            }
        )
        return text
    except Exception as exc:
        fallback = settings.reasoning_model
        write_log({"agent": role, "model": model, "error": str(exc), "fallback": fallback})
        if fallback != model and _api_key_for(fallback) and not _missing_keys_message(fallback):
            try:
                return _complete(fallback, messages, temperature, max_tokens)
            except Exception as inner:
                return f"Model call failed ({role}): {inner}"
        return f"Model call failed ({role}): {exc}"


def chat_vision(prompt: str, image_url_or_data: str) -> str:
    model = settings.vision_model
    missing = _missing_keys_message(model)
    if missing:
        return missing
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url_or_data}},
            ],
        }
    ]
    return chat("vision", messages)