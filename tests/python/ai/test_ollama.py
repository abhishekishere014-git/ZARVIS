import httpx
import pytest
from jarvis.ai.errors import ProviderUnavailableError
from jarvis.ai.models import ChatMessage, FinishReason, LLMRequest, ToolDefinition
from jarvis.ai.providers.ollama import OllamaProvider
from jarvis.core.health import HealthStatus


@pytest.mark.asyncio
async def test_ollama_generate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "model": "llama3",
            "message": {"role": "assistant", "content": "Local reply"},
            "done": True,
            "prompt_eval_count": 4,
            "eval_count": 2,
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider()
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hello local model")])
    res = await provider.generate(req)

    assert res.content == "Local reply"
    assert res.provider == "ollama"
    assert res.model == "llama3"
    assert res.finish_reason == FinishReason.STOP
    assert res.usage.total_tokens == 6
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_stream_ndjson():
    ndjson_lines = (
        '{"model":"llama3","message":{"content":"Loc"},"done":false}\n'
        '{"model":"llama3","message":{"content":"al"},"done":false}\n'
        '{"model":"llama3","message":{"content":""},"done":true,"prompt_eval_count":5,"eval_count":2}\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ndjson_lines)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider()
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Stream test")])
    tokens = []
    async for event in provider.stream(req):
        if event.text:
            tokens.append(event.text)

    assert "".join(tokens) == "Local"
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_health_probe():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3:latest"}]})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider()
    provider._client = httpx.AsyncClient(transport=transport)

    health = await provider.health()
    assert health.status == HealthStatus.HEALTHY
    assert "llama3:latest" in health.details["installed_models"]
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_offline_connection_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused by localhost:11434")

    transport = httpx.MockTransport(handler)
    provider = OllamaProvider()
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hello")])
    with pytest.raises(ProviderUnavailableError, match="Could not connect to local Ollama"):
        await provider.generate(req)
    await provider.close()
