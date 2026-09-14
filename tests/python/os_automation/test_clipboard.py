"""Tests for system clipboard read, write, size limits, and privacy controls."""

import pytest
from jarvis.os.clipboard.manager import ClipboardManager
from jarvis.os.errors import OSSecurityError
from jarvis.os.models import ClipboardReadRequest, ClipboardWriteRequest
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.security import OSSecurityManager


@pytest.fixture
def clipboard_setup(tmp_path):
    provider = MockOSProvider()
    security = OSSecurityManager(workspace_root=tmp_path, max_clipboard_chars=100)
    clipboard_mgr = ClipboardManager(provider=provider, security_manager=security)
    return clipboard_mgr, provider


def test_clipboard_write_and_read(clipboard_setup):
    clipboard_mgr, provider = clipboard_setup
    w_req = ClipboardWriteRequest(text="Hello from test clipboard")
    w_res = clipboard_mgr.write(w_req)

    assert w_res.success is True
    assert w_res.text is None  # Privacy: written text not echoed back
    assert w_res.length == len("Hello from test clipboard")
    assert provider.clipboard_content == "Hello from test clipboard"

    r_res = clipboard_mgr.read()
    assert r_res.success is True
    assert r_res.text == "Hello from test clipboard"
    assert r_res.length == len("Hello from test clipboard")


def test_clipboard_read_max_chars_truncation(clipboard_setup):
    clipboard_mgr, provider = clipboard_setup
    provider.clipboard_content = "0123456789" * 10  # 100 chars

    r_req = ClipboardReadRequest(max_chars=25)
    r_res = clipboard_mgr.read(r_req)

    assert r_res.length == 25
    assert len(r_res.text) == 25


def test_clipboard_write_exceeding_max_limit_rejected(clipboard_setup):
    clipboard_mgr, provider = clipboard_setup
    # max_clipboard_chars is 100 in our test fixture
    oversized = "A" * 105
    w_req = ClipboardWriteRequest(text=oversized)

    with pytest.raises(OSSecurityError) as exc_info:
        clipboard_mgr.write(w_req)

    assert "exceeds limit" in str(exc_info.value)


def test_clipboard_clear(clipboard_setup):
    clipboard_mgr, provider = clipboard_setup
    provider.clipboard_content = "Some sensitive password or token"
    assert clipboard_mgr.clear() is True
    assert provider.clipboard_content == ""

    r_res = clipboard_mgr.read()
    assert r_res.text == ""
