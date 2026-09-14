"""Tests for keyboard typing, key press, and hotkey execution subsystems."""

import pytest
from jarvis.os.errors import KeyNotAllowedError, OSPolicyViolationError, OSSecurityError
from jarvis.os.input.keyboard import KeyboardManager
from jarvis.os.models import KeyboardHotkeyRequest, KeyboardKeyRequest, KeyboardTypeRequest
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.security import OSSecurityManager


@pytest.fixture
def keyboard_setup(tmp_path):
    provider = MockOSProvider()
    security = OSSecurityManager(workspace_root=tmp_path, max_type_length=50)
    keyboard_mgr = KeyboardManager(provider=provider, security=security)
    return keyboard_mgr, provider


def test_keyboard_type_normal_text(keyboard_setup):
    keyboard_mgr, provider = keyboard_setup
    req = KeyboardTypeRequest(text="Hello world!", delay_ms=5)
    chars = keyboard_mgr.type_text(req)

    assert chars == 12
    assert len(provider.typed_text) == 1
    assert provider.typed_text[0] == "Hello world!"


def test_keyboard_type_sensitive_text_requires_approval(keyboard_setup):
    keyboard_mgr, provider = keyboard_setup
    # Text containing api key pattern
    req = KeyboardTypeRequest(text="sk-123456789012345678901234567890")
    
    with pytest.raises(OSPolicyViolationError):
        keyboard_mgr.type_text(req, approved=False)

    # With approval, should succeed
    chars = keyboard_mgr.type_text(req, approved=True)
    assert chars == 33
    assert provider.typed_text[-1] == "sk-123456789012345678901234567890"


def test_keyboard_type_length_limit_exceeded(keyboard_setup):
    keyboard_mgr, provider = keyboard_setup
    # Exceeds max_type_length=50
    req = KeyboardTypeRequest(text="A" * 60)
    with pytest.raises(OSSecurityError):
        keyboard_mgr.type_text(req)


def test_keyboard_press_valid_key(keyboard_setup):
    keyboard_mgr, provider = keyboard_setup
    req = KeyboardKeyRequest(key="ENTER")
    key = keyboard_mgr.press_key(req)

    assert key == "ENTER"
    assert "ENTER" in provider.pressed_keys


def test_keyboard_press_invalid_key_rejected(keyboard_setup):
    keyboard_mgr, provider = keyboard_setup
    req = KeyboardKeyRequest(key="INVALID_KEY_NAME_XYZ")
    with pytest.raises(OSSecurityError):
        keyboard_mgr.press_key(req)


def test_keyboard_hotkey_execution(keyboard_setup):
    keyboard_mgr, provider = keyboard_setup
    req = KeyboardHotkeyRequest(keys=["CTRL", "C"])
    keys = keyboard_mgr.send_hotkey(req)

    assert keys == ["CTRL", "C"]
    assert len(provider.hotkeys) == 1
    assert provider.hotkeys[0] == ["CTRL", "C"]
