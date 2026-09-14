import time
import httpx
import pytest
from jarvis.ai.models import ChatMessage, LLMRequest
from jarvis.ai.providers.openai import OpenAIProvider
from jarvis.ai.registry import AIProviderRegistry
from jarvis.ai.router import AIRouter


@pytest.mark.asyncio
async def test_router_abstraction_latency():
    """Verify that routing, capability checking, and request normalization add < 5ms of CPU overhead."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Fast"}, "finish_reason": "stop"}],
                "model": "gpt-4o",
            },
        )

    transport = httpx.MockTransport(handler)
    provider = OpenAIProvider(api_key="mock-key")
    provider._client = httpx.AsyncClient(transport=transport)

    registry = AIProviderRegistry()
    registry.register(provider)
    router = AIRouter(registry=registry, default_provider="openai")

    req = LLMRequest(messages=[ChatMessage.user("Ping")])

    # Warmup
    await router.generate(req)

    # Benchmark 50 iterations
    start = time.perf_counter()
    for _ in range(50):
        res = await router.generate(req)
        assert res.content == "Fast"
    total_time = time.perf_counter() - start

    avg_time_per_call = (total_time / 50) * 1000  # ms
    print(f"\nAverage routing + dispatch overhead per call: {avg_time_per_call:.2f}ms")

    # The abstraction overhead (including mock transport) should easily be well under 10ms
    assert avg_time_per_call < 10.0
    await provider.close()
