import pytest
from jarvis.ai.base import BaseAIProvider
from jarvis.ai.capabilities import ModelCapabilities
from jarvis.ai.errors import (
    AICancelledError,
    AuthenticationError,
    CapabilityNotSupportedError,
    ProviderUnavailableError,
)
from jarvis.ai.models import (
    AIStreamEvent,
    ChatMessage,
    LLMRequest,
    LLMResponse,
    StreamEventType,
    ToolDefinition,
)
from jarvis.ai.registry import AIProviderRegistry
from jarvis.ai.retry import RetryPolicy
from jarvis.ai.router import AIRouter


class MockProvider(BaseAIProvider):
    def __init__(
        self,
        provider_id: str,
        fail_on_generate: bool = False,
        fail_with_auth_error: bool = False,
        supports_tools: bool = True,
    ):
        super().__init__(
            provider_id=provider_id,
            default_model=f"{provider_id}-model",
            base_url="http://mock.local",
            api_key="mock-key",
        )
        self.fail_on_generate = fail_on_generate
        self.fail_with_auth_error = fail_with_auth_error
        self._supports_tools = supports_tools
        self.generate_called = 0

    def _build_headers(self):
        return {}

    async def capabilities(self, model=None):
        return ModelCapabilities(supports_tools=self._supports_tools)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.generate_called += 1
        if self.fail_with_auth_error:
            raise AuthenticationError("Bad credentials", provider=self.provider_id)
        if self.fail_on_generate:
            raise ProviderUnavailableError("Service overloaded", provider=self.provider_id)
        return LLMResponse(
            content=f"Response from {self.provider_id}",
            model=self.default_model,
            provider=self.provider_id,
        )

    async def stream(self, request: LLMRequest):
        if self.fail_on_generate:
            raise ProviderUnavailableError("Stream connection failed", provider=self.provider_id)
        yield AIStreamEvent(type=StreamEventType.TEXT_DELTA, text=f"Token from {self.provider_id}")


@pytest.mark.asyncio
async def test_router_selects_default_provider():
    registry = AIProviderRegistry()
    p1 = MockProvider("openai")
    p2 = MockProvider("anthropic")
    registry.register(p1)
    registry.register(p2)

    router = AIRouter(registry=registry, default_provider="openai")
    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    res = await router.generate(req)

    assert res.provider == "openai"
    assert p1.generate_called == 1
    assert p2.generate_called == 0


@pytest.mark.asyncio
async def test_router_selects_explicit_provider():
    registry = AIProviderRegistry()
    p1 = MockProvider("openai")
    p2 = MockProvider("anthropic")
    registry.register(p1)
    registry.register(p2)

    router = AIRouter(registry=registry, default_provider="openai")
    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    res = await router.generate(req, provider_id="anthropic")

    assert res.provider == "anthropic"
    assert p1.generate_called == 0
    assert p2.generate_called == 1


@pytest.mark.asyncio
async def test_router_automatic_fallback_on_provider_unavailable():
    registry = AIProviderRegistry()
    failing_primary = MockProvider("openai", fail_on_generate=True)
    healthy_secondary = MockProvider("anthropic", fail_on_generate=False)
    registry.register(failing_primary)
    registry.register(healthy_secondary)

    # Disable backoff delays for fast test execution
    fast_retry = RetryPolicy(max_retries=0)
    router = AIRouter(
        registry=registry,
        default_provider="openai",
        fallback_providers=["anthropic"],
        retry_policy=fast_retry,
    )

    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    res = await router.generate(req)

    # Primary failed -> automatically failover to secondary
    assert res.provider == "anthropic"
    assert res.content == "Response from anthropic"
    assert failing_primary.generate_called == 1
    assert healthy_secondary.generate_called == 1


@pytest.mark.asyncio
async def test_router_does_not_fallback_on_authentication_error():
    registry = AIProviderRegistry()
    auth_failing = MockProvider("openai", fail_with_auth_error=True)
    healthy = MockProvider("anthropic", fail_on_generate=False)
    registry.register(auth_failing)
    registry.register(healthy)

    fast_retry = RetryPolicy(max_retries=0)
    router = AIRouter(
        registry=registry,
        default_provider="openai",
        fallback_providers=["anthropic"],
        retry_policy=fast_retry,
    )

    req = LLMRequest(messages=[ChatMessage.user("Hi")])
    with pytest.raises(AuthenticationError, match="Bad credentials"):
        await router.generate(req)

    # Healthy secondary must NOT be called on auth failure
    assert healthy.generate_called == 0


@pytest.mark.asyncio
async def test_router_capability_check_blocks_unsupported_tools():
    registry = AIProviderRegistry()
    no_tool_provider = MockProvider("weak_model", supports_tools=False)
    registry.register(no_tool_provider)

    router = AIRouter(registry=registry, default_provider="weak_model", fallback_providers=[])
    req = LLMRequest(
        messages=[ChatMessage.user("Use calculator")],
        tools=[ToolDefinition(name="calc", description="calc", parameters={})],
    )

    with pytest.raises(CapabilityNotSupportedError, match="does not support tool calling"):
        await router.generate(req)


@pytest.mark.asyncio
async def test_router_stream_fallback():
    registry = AIProviderRegistry()
    failing_primary = MockProvider("openai", fail_on_generate=True)
    healthy_secondary = MockProvider("anthropic", fail_on_generate=False)
    registry.register(failing_primary)
    registry.register(healthy_secondary)

    router = AIRouter(
        registry=registry,
        default_provider="openai",
        fallback_providers=["anthropic"],
    )

    req = LLMRequest(messages=[ChatMessage.user("Stream test")])
    tokens = []
    async for event in router.stream(req):
        if event.text:
            tokens.append(event.text)

    assert "".join(tokens) == "Token from anthropic"
