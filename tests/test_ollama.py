"""Unit tests for the Ollama client using httpx.MockTransport."""

import json

import httpx
import pytest


class _MockTransport(httpx.AsyncBaseTransport):
    """Fake Ollama server responses."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            body = json.dumps(
                {"models": [{"name": "mistral"}, {"name": "llama3.2"}]}
            )
            return httpx.Response(200, text=body)

        if request.url.path == "/api/chat":
            # Simulate two token chunks then a done message.
            lines = [
                json.dumps({"message": {"content": "Hello"}, "done": False}),
                json.dumps({"message": {"content": " world"}, "done": False}),
                json.dumps({"message": {"content": ""}, "done": True}),
            ]
            return httpx.Response(200, text="\n".join(lines))

        return httpx.Response(404)


@pytest.fixture
def mock_ollama(monkeypatch):
    """Inject a mock AsyncClient into the ollama module's shared client slot."""
    import app.ollama as ollama_module

    mock_client = httpx.AsyncClient(transport=_MockTransport(), base_url="http://mock")
    monkeypatch.setattr(ollama_module, "_http_client", mock_client)


async def test_list_models(mock_ollama):
    from app.ollama import list_models
    models = await list_models()
    assert models == ["llama3.2", "mistral"]


async def test_chat_stream_yields_tokens(mock_ollama):
    from app.ollama import chat_stream
    tokens = []
    async for token in chat_stream("llama3.2", [{"role": "user", "content": "hi"}]):
        tokens.append(token)
    assert tokens == ["Hello", " world"]


async def test_chat_accumulates_full_response(mock_ollama):
    from app.ollama import chat
    result = await chat("llama3.2", [{"role": "user", "content": "hi"}])
    assert result == "Hello world"
