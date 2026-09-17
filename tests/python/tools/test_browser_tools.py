"""Tests for browser and honest YouTube automation."""

from unittest.mock import patch
import pytest
from jarvis.tools.builtins.browser_tools import (
    browser_open,
    browser_search,
    youtube_search_and_play,
    _is_safe_url,
)


def test_is_safe_url() -> None:
    assert _is_safe_url("https://www.google.com") is True
    assert _is_safe_url("http://example.com/path?arg=1") is True
    assert _is_safe_url("ftp://files.com") is False
    assert _is_safe_url("javascript:alert(1)") is False
    assert _is_safe_url("file:///C:/secret.txt") is False


@pytest.mark.asyncio
async def test_browser_open_security_rejection() -> None:
    result = await browser_open("javascript:void(0)")
    assert result["opened"] is False
    assert "violates protocol security policy" in result["error"]


@pytest.mark.asyncio
async def test_browser_search() -> None:
    with patch("webbrowser.open", return_value=True):
        result = await browser_search("test query")
        assert result["opened"] is True
        assert result["query"] == "test query"
        assert "google.com/search?q=test+query" in result["url"]


@pytest.mark.asyncio
async def test_youtube_search_and_play_honest_reporting() -> None:
    with patch("webbrowser.open", return_value=True):
        result = await youtube_search_and_play("lofi beats")
        assert result["opened"] is True
        assert result["query"] == "lofi beats"
        assert "youtube.com/results?search_query=lofi+beats" in result["url"]
        # Must honestly report that playback cannot be verified without browser extension
        assert result["playback_verified"] is False
        assert "Please select a video" in result["message"]
