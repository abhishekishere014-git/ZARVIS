import json
import httpx
import pytest
from jarvis.ai.errors import AuthenticationError, RateLimitError
from jarvis.ai.models import ChatMessage, FinishReason, LLMRequest, ToolDefinition
from jarvis.ai.providers.anthropic import AnthropicProvider


@pytest.mark.asyncio
async def test_anthropic_generate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "id": "msg_123",
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "Anthropic response"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 6},
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    provider = AnthropicProvider(api_key="sk-ant-mock")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hello Claude")])
    res = await provider.generate(req)

    assert res.content == "Anthropic response"
    assert res.provider == "anthropic"
    assert res.usage.prompt_tokens == 12
    assert res.usage.completion_tokens == 6
    assert res.finish_reason == FinishReason.STOP
    await provider.close()


@pytest.mark.asyncio
async def test_anthropic_generate_tool_use():
    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "id": "msg_tool",
            "model": "claude-3-5-sonnet-20241022",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_01",
                    "name": "lookup",
                    "input": {"query": "JARVIS"},
                }
            ],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 20, "output_tokens": 10},
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    provider = AnthropicProvider(api_key="sk-ant-mock")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(
        messages=[ChatMessage.user("Find JARVIS")],
        tools=[ToolDefinition(name="lookup", description="Lookup", parameters={})],
    )
    res = await provider.generate(req)

    assert res.tool_calls is not None
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].id == "toolu_01"
    assert res.tool_calls[0].name == "lookup"
    assert res.tool_calls[0].arguments == {"query": "JARVIS"}
    assert res.finish_reason == FinishReason.TOOL_CALLS
    await provider.close()


@pytest.mark.asyncio
async def test_anthropic_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    transport = httpx.MockTransport(handler)
    provider = AnthropicProvider(api_key="sk-ant-mock")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hello")])
    with pytest.raises(RateLimitError, match="Rate limit exceeded"):
        await provider.generate(req)
    await provider.close()
