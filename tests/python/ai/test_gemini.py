import httpx
import pytest
from jarvis.ai.errors import AuthenticationError
from jarvis.ai.models import ChatMessage, FinishReason, LLMRequest, ToolDefinition
from jarvis.ai.providers.gemini import GeminiProvider


@pytest.mark.asyncio
async def test_gemini_generate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Gemini answer"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 3,
                "totalTokenCount": 8,
            },
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    provider = GeminiProvider(api_key="mock-gemini-key")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hi Gemini")])
    res = await provider.generate(req)

    assert res.content == "Gemini answer"
    assert res.provider == "gemini"
    assert res.finish_reason == FinishReason.STOP
    assert res.usage.total_tokens == 8
    await provider.close()


@pytest.mark.asyncio
async def test_gemini_generate_function_call():
    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "calc",
                                    "args": {"expression": "10 * 5"},
                                }
                            }
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    provider = GeminiProvider(api_key="mock-gemini-key")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(
        messages=[ChatMessage.user("10*5")],
        tools=[ToolDefinition(name="calc", description="calculator", parameters={})],
    )
    res = await provider.generate(req)

    assert res.tool_calls is not None
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "calc"
    assert res.tool_calls[0].arguments == {"expression": "10 * 5"}
    await provider.close()


@pytest.mark.asyncio
async def test_gemini_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "API key not valid"}})

    transport = httpx.MockTransport(handler)
    provider = GeminiProvider(api_key="invalid-key")
    provider._client = httpx.AsyncClient(transport=transport)

    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    with pytest.raises(AuthenticationError, match="API key not valid"):
        await provider.generate(req)
    await provider.close()
