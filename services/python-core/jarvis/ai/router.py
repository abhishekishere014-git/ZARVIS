"""Intelligent, capability-aware AI Router with controlled multi-provider failover."""

import asyncio
import logging
from typing import AsyncIterator, List, Optional
from jarvis.ai.base import AIProvider
from jarvis.ai.errors import (
    AICancelledError,
    AIError,
    CapabilityNotSupportedError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from jarvis.ai.models import AIStreamEvent, LLMRequest, LLMResponse
from jarvis.ai.registry import AIProviderRegistry
from jarvis.ai.retry import RetryPolicy

logger = logging.getLogger("jarvis.ai.router")


class AIRouter:
    """Dispatches generation requests with capability verification, retries, and fallback chains."""

    def __init__(
        self,
        registry: AIProviderRegistry,
        default_provider: str = "openai",
        fallback_providers: Optional[List[str]] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self.registry = registry
        self.default_provider = default_provider
        self.fallback_providers = fallback_providers or ["anthropic", "gemini", "ollama"]
        self.retry_policy = retry_policy or RetryPolicy()

    def _resolve_provider_candidates(
        self,
        requested_provider: Optional[str] = None,
    ) -> List[AIProvider]:
        """Determine the ordered list of provider candidates to attempt."""
        if requested_provider:
            provider = self.registry.get(requested_provider)
            if not provider:
                raise ProviderUnavailableError(f"Requested provider '{requested_provider}' is not registered.")
            return [provider]

        candidates: List[AIProvider] = []
        # 1. Default provider
        primary = self.registry.get(self.default_provider)
        if primary:
            candidates.append(primary)

        # 2. Fallbacks
        for fb_id in self.fallback_providers:
            if fb_id != self.default_provider:
                fb_provider = self.registry.get(fb_id)
                if fb_provider and fb_provider not in candidates:
                    candidates.append(fb_provider)

        if not candidates:
            raise ProviderUnavailableError("No AI providers available in registry to serve request.")

        return candidates

    async def _verify_capabilities(self, provider: AIProvider, request: LLMRequest) -> None:
        """Ensure provider and model satisfy requested capabilities."""
        caps = await provider.capabilities(request.model)
        if request.tools and not caps.supports_tools:
            raise CapabilityNotSupportedError(
                f"Model '{request.model or provider.default_model}' on '{provider.provider_id}' does not support tool calling.",
                provider=provider.provider_id,
                model=request.model,
            )

    async def generate(
        self,
        request: LLMRequest,
        provider_id: Optional[str] = None,
    ) -> LLMResponse:
        """Execute text/tool generation with automated fallback on infrastructure errors."""
        candidates = self._resolve_provider_candidates(provider_id)
        last_exception: Optional[Exception] = None

        for idx, provider in enumerate(candidates):
            logger.info(
                "Routing request to provider '%s' (Candidate %d/%d)...",
                provider.provider_id,
                idx + 1,
                len(candidates),
            )

            try:
                # 1. Verify capabilities
                await self._verify_capabilities(provider, request)

                # 2. Execute with bounded retries
                async def execute_call() -> LLMResponse:
                    return await provider.generate(request)

                response = await self.retry_policy.execute(
                    execute_call,
                    operation_name=f"{provider.provider_id}.generate",
                )
                return response

            except AICancelledError:
                # Never fallback on user cancellation
                raise
            except CapabilityNotSupportedError as exc:
                last_exception = exc
                logger.warning(
                    "Provider '%s' lacks capabilities for request: %s. Attempting fallback...",
                    provider.provider_id,
                    request.model,
                )
                continue
            except AIError as exc:
                last_exception = exc
                if not exc.is_retryable and exc.status_code in (400, 401, 403):
                    # Authentication or client syntax errors should not blindly fallback to other models
                    logger.error(
                        "Fatal non-fallback error from '%s': %s (status: %s)",
                        provider.provider_id,
                        exc.message,
                        exc.status_code,
                    )
                    raise

                logger.warning(
                    "Provider '%s' failed (%s: %s). Attempting fallback...",
                    provider.provider_id,
                    exc.__class__.__name__,
                    exc.message,
                )

        if last_exception:
            raise last_exception
        raise ProviderUnavailableError("All available AI provider candidates failed to satisfy the request.")

    async def stream(
        self,
        request: LLMRequest,
        provider_id: Optional[str] = None,
    ) -> AsyncIterator[AIStreamEvent]:
        """Stream generation with initial connection failover."""
        candidates = self._resolve_provider_candidates(provider_id)
        last_exception: Optional[Exception] = None

        for idx, provider in enumerate(candidates):
            try:
                await self._verify_capabilities(provider, request)

                # Attempt to open stream; yield tokens as they arrive
                stream_generator = provider.stream(request)
                async for event in stream_generator:
                    yield event
                return
            except (asyncio.CancelledError, AICancelledError):
                raise AICancelledError()
            except AIError as exc:
                last_exception = exc
                if not exc.is_retryable and exc.status_code in (400, 401, 403):
                    raise
                logger.warning(
                    "Stream initiation failed for '%s': %s. Falling back...",
                    provider.provider_id,
                    exc.message,
                )

        if last_exception:
            raise last_exception
        raise ProviderUnavailableError("All streaming AI provider candidates failed.")
