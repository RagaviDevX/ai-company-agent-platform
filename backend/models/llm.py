import hashlib
import json
from typing import Any, Iterator

import httpx
from groq import Groq

from backend.cache.cache import get_cache
from backend.config.settings import settings
from backend.memory.store import MemoryStore
from backend.utils.logger import write_log

MODELS = {
    "planner": settings.planner_model,
    "coder": settings.coder_model,
    "reasoning": settings.reasoning_model,
    "vision": settings.vision_model,
}

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Roles whose configured model is a text-only chat model. `chat()` only
# ever falls back to `settings.reasoning_model` for these roles: falling
# back for "vision" would resend an image_url content block to a
# text-only model, which fails again (or errors in a confusing way).
_TEXT_ROLES = {"planner", "coder", "reasoning"}

_STORE: MemoryStore | None = None


def _store() -> MemoryStore:
    global _STORE
    if _STORE is None:
        _STORE = MemoryStore()
    return _STORE


def _record(role: str, model: str, input_text: str, output_text: str) -> None:
    """Persist a call to both the file log and the `agent_logs` table.

    Logging must never break a model call: DB failures are swallowed after
    the file log (which has no external dependency) has already succeeded.
    """
    write_log(
        {
            "agent": role,
            "model": model,
            "input_preview": input_text[:400],
            "output_preview": output_text[:400],
        }
    )
    try:
        _store().add_agent_log(None, role, model, input_text, output_text)
    except Exception:
        pass


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


def _cache_key(role: str, model: str, messages: list[dict[str, Any]], temperature: float, max_tokens: int) -> str:
    payload = json.dumps(
        {"role": role, "model": model, "messages": messages, "t": temperature, "m": max_tokens},
        sort_keys=True,
    )
    return "llm:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chat(
    role: str,
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    model = MODELS.get(role, settings.reasoning_model)
    input_preview = str(messages[-1].get("content", "")) if messages else ""

    missing = _missing_keys_message(model)
    if missing:
        write_log({"agent": role, "model": model, "error": "missing_api_key"})
        return missing

    # Only exact-duplicate (role, model, messages, params) calls hit the
    # cache -- fine for repeated identical questions, harmless (a miss)
    # for anything else. Not applied to chat_stream(): streaming exists
    # specifically to show partial output as it's generated, and serving
    # a cached response would either defeat that or need to be faked as a
    # fake stream, neither of which is worth the complexity here.
    cache = get_cache()
    cache_key = _cache_key(role, model, messages, temperature, max_tokens)
    cached = cache.get_json(cache_key)
    if cached is not None:
        return cached

    try:
        text = _complete(model, messages, temperature, max_tokens)
        _record(role, model, input_preview, text)
        cache.set_json(cache_key, text)
        return text
    except Exception as exc:
        fallback = settings.reasoning_model
        write_log({"agent": role, "model": model, "error": str(exc), "fallback": fallback})
        can_fallback = (
            role in _TEXT_ROLES
            and fallback != model
            and _api_key_for(fallback)
            and not _missing_keys_message(fallback)
        )
        if can_fallback:
            try:
                text = _complete(fallback, messages, temperature, max_tokens)
                _record(role, fallback, input_preview, text)
                cache.set_json(cache_key, text)
                return text
            except Exception as inner:
                error_text = f"Model call failed ({role}): {inner}"
                _record(role, fallback, input_preview, error_text)
                return error_text
        error_text = f"Model call failed ({role}): {exc}"
        _record(role, model, input_preview, error_text)
        return error_text


def chat_stream(
    role: str,
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> Iterator[str]:
    """Yield text deltas as they arrive, for the SSE `/chat/stream` route.

    Groq's API streams natively (OpenAI-compatible `stream=True`).
    OpenRouter's HTTP API streams via SSE too, so both are wired up here.
    Unlike `chat()`, a mid-stream failure is surfaced as an error chunk
    rather than silently retried on a fallback model: tokens may already
    have been sent to the client, so restarting the response from scratch
    on a different model would be a worse experience than just reporting
    the failure.
    """
    model = MODELS.get(role, settings.reasoning_model)
    missing = _missing_keys_message(model)
    if missing:
        yield missing
        return

    provider = _provider(model)
    input_preview = str(messages[-1].get("content", "")) if messages else ""
    chunks: list[str] = []
    try:
        if provider == "groq":
            client = Groq(api_key=settings.groq_api_key)
            stream = client.chat.completions.create(
                model=_bare_model(model),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for event in stream:
                delta = _content_text(event.choices[0].delta.content)
                if delta:
                    chunks.append(delta)
                    yield delta
        elif provider == "openrouter":
            payload = {
                "model": _bare_model(model),
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:8000",
                "X-Title": settings.app_name,
            }
            with httpx.Client(timeout=120) as client:
                with client.stream("POST", OPENROUTER_URL, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[len("data: ") :].strip()
                        if data == "[DONE]":
                            break
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        delta = event.get("choices", [{}])[0].get("delta", {}).get("content")
                        if delta:
                            chunks.append(delta)
                            yield delta
        else:
            # Hugging Face role has no streaming path wired up in this app
            # (embeddings run locally; HF is not currently used for chat
            # completions) -- fall back to a single non-streamed chunk.
            text = _complete(model, messages, temperature, max_tokens)
            chunks.append(text)
            yield text
    except Exception as exc:
        error_text = f"Model call failed ({role}): {exc}"
        chunks.append(error_text)
        yield error_text
    finally:
        _record(role, model, input_preview, "".join(chunks))


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