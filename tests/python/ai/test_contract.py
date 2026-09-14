import json
import httpx
import pytest
from jarvis.ai.base import AIProvider
from jarvis.ai.models import ChatMessage, FinishReason, LLMRequest, ToolDefinition
from jarvis.ai.providers.anthropic import AnthropicProvider
from jarvis.ai.providers.gemini import GeminiProvider
from jarvis.ai.providers.ollama import OllamaProvider
from jarvis.ai.providers.openai import OpenAIProvider


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_cls, mock_response_builder",
    [
        (
            OpenAIProvider,
            lambda req: httpx.Response(
                200,
                json={
                    "choices": [{"message": {"role": "assistant", "content": "OpenAI says hello"}, "finish_reason": "stop"}],
                    "model": "gpt-4o",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                },
            ),
        ),
        (
            AnthropicProvider,
            lambda req: httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "Anthropic says hello"}],
                    "model": "claude-3-5-sonnet",
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            ),
        ),
        (
            GeminiProvider,
            lambda req: httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": "Gemini says hello"}]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15},
                },
            ),
        ),
        (
            OllamaProvider,
            lambda req: httpx.Response(
                200,
                json={
                    "message": {"role": "assistant", "content": "Ollama says hello"},
                    "model": "llama3",
                    "done": True,
                    "prompt_eval_count": 10,
                    "eval_count": 5,
                },
            ),
        ),
    ],
)
async def test_universal_provider_contract(provider_cls, mock_response_builder):
    transport = httpx.MockTransport(mock_response_builder)
    if provider_cls == OllamaProvider:
        provider = provider_cls()
    else:
        provider = provider_cls(api_key="mock-key")
    provider._client = httpx.AsyncClient(transport=transport)

    # 1. Verify runtime checkable AIProvider protocol adherence
    assert isinstance(provider, AIProvider)

    # 2. Test standard text generation contract
    req = LLMRequest(messages=[ChatMessage.user("Say hello")])
    res = await provider.generate(req)

    assert res.content is not None
    assert "says hello" in res.content
    assert res.finish_reason == FinishReason.STOP
    assert res.usage.total_tokens == 15
    assert res.provider == provider.provider_id

    # 3. Test capabilities query
    caps = await provider.capabilities()
    assert caps.supports_streaming is True
    assert caps.context_window > 0

    await provider.close()
