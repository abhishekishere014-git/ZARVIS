"""Tests for application launcher and allowlist verification."""

import pytest
from jarvis.os.tools.app_tools import app_launch, app_focus, app_close, _resolve_app


@pytest.mark.asyncio
async def test_app_allowlist_resolution() -> None:
    # Test valid apps and aliases
    assert _resolve_app("Calculator") is not None
    assert _resolve_app("calc") is not None
    assert _resolve_app("Visual Studio Code") is not None
    assert _resolve_app("vscode") is not None
    assert _resolve_app("Notepad") is not None
    assert _resolve_app("Chrome") is not None

    # Test unknown or unauthorized commands
    assert _resolve_app("evil_trojan.exe") is None
    assert _resolve_app("format C:") is None
    assert _resolve_app("powershell -Command Remove-Item") is None


@pytest.mark.asyncio
async def test_app_launch_rejection() -> None:
    result = await app_launch("unauthorized_app_xyz")
    assert result["launched"] is False
    assert "not in the approved allowlist" in result["error"]


@pytest.mark.asyncio
async def test_app_launch_allowlisted() -> None:
    result = await app_launch("Calculator")
    assert result["launched"] is True
    assert result["app"] == "Calculator"
