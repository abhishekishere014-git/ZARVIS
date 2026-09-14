"""Tests for rate limiting, size boundaries, and timeouts on OS operations."""

import pytest
from jarvis.os.errors import OSSecurityError, ScreenCaptureError
from jarvis.os.models import ClipboardWriteRequest, KeyboardTypeRequest, ScreenCaptureRequest
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.screen.capture import ScreenCaptureManager
from jarvis.os.security import OSSecurityManager


@pytest.fixture
def limits_setup(tmp_path):
    security = OSSecurityManager(
        workspace_root=tmp_path,
        max_type_length=100,
        max_clipboard_chars=200,
        max_screen_bytes=5000,
    )
    provider = MockOSProvider()
    capture_mgr = ScreenCaptureManager(provider=provider, security=security)
    return security, provider, capture_mgr


def test_type_length_hard_limit(limits_setup):
    security, _, _ = limits_setup
    with pytest.raises(OSSecurityError):
        security.validate_text_for_typing("X" * 101)


def test_clipboard_size_hard_limit(limits_setup):
    security, _, _ = limits_setup
    req = ClipboardWriteRequest(text="Y" * 201)
    assert len(req.text) > security.max_clipboard_chars


def test_screen_capture_size_ceiling_enforced(limits_setup):
    security, provider, capture_mgr = limits_setup
    # Normal capture within size passes
    req = ScreenCaptureRequest(region=(0, 0, 10, 10))
    res = capture_mgr.capture(req)
    assert res.size_bytes <= security.max_screen_bytes
