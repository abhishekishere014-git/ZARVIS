import json
import httpx
import pytest
from jarvis.ai.errors import AuthenticationError, RateLimitError
from jarvis.ai.models import ChatMessage, FinishReason, LLMRequest, ToolDefinition
from jarvis.ai.providers.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_generate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "id": "chatcmpl-123",
            "model": "gpt-4o",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello world!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10},
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    provider = OpenAIProvider(api_key="sk-mock-key")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    res = await provider.generate(req)

    assert res.content == "Hello world!"
    assert res.model == "gpt-4o"
    assert res.provider == "openai"
    assert res.usage.total_tokens == 10
    assert res.finish_reason == FinishReason.STOP
    await provider.close()


@pytest.mark.asyncio
async def test_openai_generate_tool_calls():
    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "id": "chatcmpl-tool",
            "model": "gpt-4o",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": json.dumps({"city": "Berlin"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    provider = OpenAIProvider(api_key="sk-mock-key")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(
        messages=[ChatMessage.user("Weather in Berlin")],
        tools=[ToolDefinition(name="get_weather", description="Get weather", parameters={})],
    )
    res = await provider.generate(req)

    assert res.tool_calls is not None
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "get_weather"
    assert res.tool_calls[0].arguments == {"city": "Berlin"}
    assert res.finish_reason == FinishReason.TOOL_CALLS
    await provider.close()


@pytest.mark.asyncio
async def test_openai_stream_tokens():
    sse_lines = [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n',
        'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n',
        "data: [DONE]\n\n",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="".join(sse_lines), headers={"content-type": "text/event-stream"})

    transport = httpx.MockTransport(handler)
    provider = OpenAIProvider(api_key="sk-mock-key")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    tokens = []
    async for event in provider.stream(req):
        if event.text:
            tokens.append(event.text)

    assert "".join(tokens) == "Hello"
    await provider.close()


@pytest.mark.asyncio
async def test_openai_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API key"}})

    transport = httpx.MockTransport(handler)
    provider = OpenAIProvider(api_key="invalid-key")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    with pytest.raises(AuthenticationError, match="Invalid API key"):
        await provider.generate(req)
    await provider.close()
