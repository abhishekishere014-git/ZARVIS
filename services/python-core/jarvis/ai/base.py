"""AI Provider Protocol and Base Abstract Provider."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Protocol, runtime_checkable
import httpx
from jarvis.ai.capabilities import ModelCapabilities, get_default_capabilities
from jarvis.ai.models import AIStreamEvent, LLMRequest, LLMResponse
from jarvis.core.health import ComponentHealth, HealthStatus


@runtime_checkable
class AIProvider(Protocol):
    """Universal protocol contract required for all AI provider adapters."""

    provider_id: str
    default_model: str

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute a standard non-streaming text/tool generation."""
        ...

    async def stream(self, request: LLMRequest) -> AsyncIterator[AIStreamEvent]:
        """Stream incremental tokens and tool call deltas."""
        ...

    async def capabilities(self, model: Optional[str] = None) -> ModelCapabilities:
        """Retrieve capability flags for a specific model."""
        ...

    async def health(self) -> ComponentHealth:
        """Check provider reachability and operational readiness."""
        ...

    async def close(self) -> None:
        """Cleanly release persistent HTTP connections and resources."""
        ...


class BaseAIProvider(ABC):
    """Abstract foundational provider handling HTTP connection pooling and lifecycle."""

    def __init__(
        self,
        provider_id: str,
        default_model: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.provider_id = provider_id
        self.default_model = default_model
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.default_timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def has_credentials(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.default_timeout, connect=10.0),
                follow_redirects=True,
                headers=self._build_headers(),
            )
        return self._client

    @abstractmethod
    def _build_headers(self) -> dict[str, str]:
        """Construct vendor-specific authentication and content headers."""
        pass

    async def capabilities(self, model: Optional[str] = None) -> ModelCapabilities:
        target_model = model or self.default_model
        return get_default_capabilities(target_model, is_local=(self.provider_id == "ollama"))

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health(self) -> ComponentHealth:
        return ComponentHealth(
            name=f"ai_provider.{self.provider_id}",
            status=HealthStatus.HEALTHY if (self.has_credentials or self.provider_id == "ollama") else HealthStatus.DEGRADED,
            details={
                "provider": self.provider_id,
                "default_model": self.default_model,
                "has_credentials": self.has_credentials,
            },
        )
