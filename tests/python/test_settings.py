import os
from pathlib import Path
import pytest
from jarvis.config.settings import JarvisSettings


def test_default_settings():
    settings = JarvisSettings()
    assert settings.env == "development"
    assert settings.debug is True
    assert settings.core_host == "127.0.0.1"
    assert settings.core_port == 8765
    assert settings.vault_backend in ("keyring", "memory")
    assert settings.is_development is True
    assert settings.is_production is False


def test_custom_settings_via_env(monkeypatch):
    monkeypatch.setenv("JARVIS_ENV", "production")
    monkeypatch.setenv("JARVIS_DEBUG", "false")
    monkeypatch.setenv("JARVIS_CORE_PORT", "9999")
    monkeypatch.setenv("JARVIS_VAULT_BACKEND", "memory")

    settings = JarvisSettings()
    assert settings.env == "production"
    assert settings.debug is False
    assert settings.core_port == 9999
    assert settings.vault_backend == "memory"
    assert settings.is_production is True
    assert settings.is_development is False
