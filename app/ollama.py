"""Async client for the Ollama API.

Exposes:
  list_models()  — returns sorted list of installed model names
  chat_stream()  — async generator yielding text deltas from a streaming chat call
  startup() / shutdown() — called from the FastAPI lifespan to manage the shared client
"""

import json
from collections.abc import AsyncGenerator

import httpx

from app.config import settings

# Shared client — created once at startup, reused across all requests.
_http_client: httpx.AsyncClient | None = None


async def startup() -> None:
    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=settings.ollama_host,
        timeout=httpx.Timeout(settings.ollama_timeout_s),
    )


async def shutdown() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def _get_client() -> httpx.AsyncClient:
    assert _http_client is not None, "Ollama client accessed before startup()"
    return _http_client


async def list_models() -> list[str]:
    """Return model names sorted alphabetically, e.g. ['llama3.2', 'mistral']."""
    resp = await _get_client().get("/api/tags")
    resp.raise_for_status()
    return sorted(m["name"] for m in resp.json().get("models", []))


async def chat_stream(
    model: str,
    messages: list[dict],
    system_prompt: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream text deltas from Ollama /api/chat.

    Yields plain-text token strings as they arrive. The caller is responsible
    for accumulating and persisting the full response.
    """
    payload_messages = []
    if system_prompt:
        payload_messages.append({"role": "system", "content": system_prompt})
    payload_messages.extend(messages)

    async with _get_client().stream(
        "POST",
        "/api/chat",
        json={"model": model, "messages": payload_messages, "stream": True},
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                yield delta
            if chunk.get("done"):
                break


async def chat(
    model: str,
    messages: list[dict],
    system_prompt: str | None = None,
) -> str:
    """Non-streaming convenience wrapper — accumulates and returns the full response."""
    parts: list[str] = []
    async for delta in chat_stream(model, messages, system_prompt):
        parts.append(delta)
    return "".join(parts)
