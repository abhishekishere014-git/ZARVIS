"""Factory for instantiating and configuring AI providers from settings and vault."""

import logging
from typing import Optional
from jarvis.ai.providers.anthropic import AnthropicProvider
from jarvis.ai.providers.gemini import GeminiProvider
from jarvis.ai.providers.ollama import OllamaProvider
from jarvis.ai.providers.openai import OpenAIProvider
from jarvis.ai.registry import AIProviderRegistry
from jarvis.ai.router import AIRouter
from jarvis.config.settings import JarvisSettings
from jarvis.security.vault import SecretVault

logger = logging.getLogger("jarvis.ai.factory")


def build_ai_system(
    settings: JarvisSettings,
    vault: SecretVault,
) -> tuple[AIProviderRegistry, AIRouter]:
    """Construct and register all available AI providers based on vault secrets and settings."""
    registry = AIProviderRegistry()

    # 1. OpenAI
    openai_key = vault.get_secret("OPENAI_API_KEY")
    if openai_key:
        registry.register(
            OpenAIProvider(
                api_key=openai_key,
                default_model=getattr(settings, "openai_default_model", "gpt-4o"),
            )
        )
    else:
        logger.debug("OpenAI credentials not configured in vault; skipping adapter registration.")

    # 2. Anthropic
    anthropic_key = vault.get_secret("ANTHROPIC_API_KEY")
    if anthropic_key:
        registry.register(
            AnthropicProvider(
                api_key=anthropic_key,
                default_model=getattr(settings, "anthropic_default_model", "claude-3-5-sonnet-20241022"),
            )
        )
    else:
        logger.debug("Anthropic credentials not configured in vault; skipping adapter registration.")

    # 3. Google Gemini
    gemini_key = vault.get_secret("GEMINI_API_KEY")
    if gemini_key:
        registry.register(
            GeminiProvider(
                api_key=gemini_key,
                default_model=getattr(settings, "gemini_default_model", "gemini-2.0-flash"),
            )
        )
    else:
        logger.debug("Gemini credentials not configured in vault; skipping adapter registration.")

    # 4. Ollama (Always registered as local zero-cost/offline inference candidate)
    ollama_url = getattr(settings, "ollama_base_url", "http://127.0.0.1:11434")
    ollama_model = getattr(settings, "ollama_default_model", "llama3")
    registry.register(
        OllamaProvider(
            base_url=ollama_url,
            default_model=ollama_model,
        )
    )

    # Determine default provider
    default_provider = "openai" if openai_key else "ollama"
    router = AIRouter(
        registry=registry,
        default_provider=default_provider,
        fallback_providers=["anthropic", "gemini", "ollama", "openai"],
    )

    return registry, router
