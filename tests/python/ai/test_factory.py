import pytest
from jarvis.ai.factory import build_ai_system
from jarvis.config.settings import JarvisSettings
from jarvis.security.vault import InMemoryVault


def test_factory_with_only_ollama():
    vault = InMemoryVault()
    settings = JarvisSettings()

    registry, router = build_ai_system(settings, vault)

    assert registry.has_provider("ollama")
    assert not registry.has_provider("openai")
    assert not registry.has_provider("anthropic")
    assert not registry.has_provider("gemini")
    assert router.default_provider == "ollama"


def test_factory_with_openai_configured():
    vault = InMemoryVault()
    vault.set_secret("OPENAI_API_KEY", "sk-mock-openai-key")
    settings = JarvisSettings()

    registry, router = build_ai_system(settings, vault)

    assert registry.has_provider("openai")
    assert registry.has_provider("ollama")
    assert not registry.has_provider("anthropic")
    assert router.default_provider == "openai"


def test_factory_with_all_credentials():
    vault = InMemoryVault()
    vault.set_secret("OPENAI_API_KEY", "sk-openai")
    vault.set_secret("ANTHROPIC_API_KEY", "sk-anthropic")
    vault.set_secret("GEMINI_API_KEY", "sk-gemini")
    settings = JarvisSettings()

    registry, router = build_ai_system(settings, vault)

    assert registry.has_provider("openai")
    assert registry.has_provider("anthropic")
    assert registry.has_provider("gemini")
    assert registry.has_provider("ollama")
    assert router.default_provider == "openai"
