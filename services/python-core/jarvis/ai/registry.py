"""Central registry for discovering and managing AI provider adapters."""

import logging
from typing import Dict, List, Optional
from jarvis.ai.base import AIProvider
from jarvis.ai.errors import AIError

logger = logging.getLogger("jarvis.ai.registry")


class AIProviderRegistry:
    """Thread-safe provider catalog supporting dynamic registration and lookup."""

    def __init__(self) -> None:
        self._providers: Dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        """Register an AI provider adapter instance."""
        if not isinstance(provider, AIProvider):
            raise TypeError(f"Provider {provider} does not implement the AIProvider Protocol.")
        self._providers[provider.provider_id] = provider
        logger.info("Registered AI provider: '%s' (Default model: '%s')", provider.provider_id, provider.default_model)

    def unregister(self, provider_id: str) -> Optional[AIProvider]:
        """Remove a provider from active registry."""
        return self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> Optional[AIProvider]:
        """Retrieve provider by its unique identifier."""
        return self._providers.get(provider_id)

    def list_providers(self) -> List[str]:
        """List all currently registered provider identifiers."""
        return list(self._providers.keys())

    def has_provider(self, provider_id: str) -> bool:
        """Check if provider is registered."""
        return provider_id in self._providers

    async def close_all(self) -> None:
        """Close connections on all registered providers."""
        for name, provider in list(self._providers.items()):
            try:
                await provider.close()
            except Exception as e:
                logger.error("Error closing provider '%s': %s", name, e)
        self._providers.clear()
