import pytest
from jarvis.ai.base import BaseAIProvider
from jarvis.ai.models import LLMRequest, LLMResponse
from jarvis.ai.registry import AIProviderRegistry


class FakeProvider(BaseAIProvider):
    def __init__(self, provider_id: str, default_model: str = "fake-v1"):
        super().__init__(
            provider_id=provider_id,
            default_model=default_model,
            base_url="http://fake.local",
            api_key="fake-key",
        )

    def _build_headers(self):
        return {"Authorization": "Bearer fake"}

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="fake reply", model=self.default_model, provider=self.provider_id)

    async def stream(self, request: LLMRequest):
        if False:
            yield


def test_registry_lifecycle():
    registry = AIProviderRegistry()
    p1 = FakeProvider("provider_one")
    p2 = FakeProvider("provider_two")

    registry.register(p1)
    registry.register(p2)

    assert registry.has_provider("provider_one")
    assert registry.has_provider("provider_two")
    assert not registry.has_provider("non_existent")

    assert registry.get("provider_one") is p1
    assert sorted(registry.list_providers()) == ["provider_one", "provider_two"]

    unreg = registry.unregister("provider_one")
    assert unreg is p1
    assert not registry.has_provider("provider_one")
    assert registry.get("provider_one") is None


def test_registry_rejects_invalid_type():
    registry = AIProviderRegistry()
    with pytest.raises(TypeError, match="does not implement the AIProvider Protocol"):
        registry.register("not-a-provider")
