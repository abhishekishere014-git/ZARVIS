"""Deterministic local testbed test suite for browser automation and honest verification."""

import http.server
import socketserver
import threading
from typing import Generator
from unittest.mock import patch
import pytest

from jarvis.tools.builtins.browser_tools import (
    browser_open,
    browser_search,
    youtube_search_and_play,
    _is_safe_url,
)


class DeterministicTestbedHandler(http.server.BaseHTTPRequestHandler):
    """Local deterministic HTTP mock server for browser automation verification."""

    def do_GET(self):
        if self.path.startswith("/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "testbed"}')
        elif self.path.startswith("/search"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Search Results</h1><ul id='results'><li>Result 1</li></ul></body></html>")
        elif self.path.startswith("/player"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><video id='player' src='test.mp4' data-state='playing'></video></body></html>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def local_testbed() -> Generator[str, None, None]:
    """Spins up a deterministic local loopback HTTP server fixture."""
    server = socketserver.TCPServer(("127.0.0.1", 0), DeterministicTestbedHandler)
    host, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    server.shutdown()
    server.server_close()


def test_scheme_security_boundary():
    """Verify that dangerous URI schemes are strictly rejected by security policy."""
    assert _is_safe_url("http://127.0.0.1:8080/test") is True
    assert _is_safe_url("https://www.youtube.com/watch?v=123") is True
    assert _is_safe_url("javascript:alert(document.cookie)") is False
    assert _is_safe_url("data:text/html,<script>alert(1)</script>") is False
    assert _is_safe_url("file:///C:/Windows/System32/cmd.exe") is False
    assert _is_safe_url("vbscript:MsgBox(1)") is False
    assert _is_safe_url("powershell.exe") is False


@pytest.mark.asyncio
async def test_deterministic_testbed_health(local_testbed: str):
    """Verify the deterministic testbed server responds correctly on loopback."""
    import urllib.request
    import json

    health_url = f"{local_testbed}/health"
    with urllib.request.urlopen(health_url) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_browser_open_on_testbed(local_testbed: str):
    """Verify browser_open safely navigates to the deterministic testbed fixture."""
    target_url = f"{local_testbed}/player?v=demo_track"
    with patch("webbrowser.open", return_value=True) as mock_open:
        res = await browser_open(target_url)
        assert res["opened"] is True
        assert res["url"] == target_url
        assert "default browser" in res["message"]
        mock_open.assert_called_once_with(target_url, new=2)


@pytest.mark.asyncio
async def test_browser_open_blocks_malicious_urls():
    """Verify browser_open aborts and reports security violation without launching browser."""
    with patch("webbrowser.open") as mock_open:
        res = await browser_open("javascript:window.open('evil.com')")
        assert res["opened"] is False
        assert "violates protocol security policy" in res["error"]
        mock_open.assert_not_called()


@pytest.mark.asyncio
async def test_youtube_automation_honest_reporting():
    """Verify youtube_search_and_play strictly reports playback_verified=False."""
    with patch("webbrowser.open", return_value=True) as mock_open:
        res = await youtube_search_and_play("Interstellar Main Theme")
        assert res["opened"] is True
        assert res["query"] == "Interstellar Main Theme"
        assert "youtube.com/results?search_query=Interstellar+Main+Theme" in res["url"]
        assert res["playback_verified"] is False
        assert "Please select a video to begin playback" in res["message"]
        mock_open.assert_called_once()
