"""Tests for post-action state verification (mouse position, window focus, clipboard content)."""

import pytest
from jarvis.os.models import OSVerificationResult
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.verification.verifier import OSActionVerifier


@pytest.fixture
def verifier_setup():
    provider = MockOSProvider()
    verifier = OSActionVerifier(provider=provider)
    return verifier, provider


def test_verify_mouse_position_success(verifier_setup):
    verifier, provider = verifier_setup
    provider.cursor_x = 500
    provider.cursor_y = 300

    result = verifier.verify_mouse_position(500, 300)
    assert result.verified is True
    assert result.confidence == 1.0


def test_verify_mouse_position_failure(verifier_setup):
    verifier, provider = verifier_setup
    provider.cursor_x = 450
    provider.cursor_y = 300

    result = verifier.verify_mouse_position(500, 300)
    assert result.verified is False
    assert result.confidence == 0.0


def test_verify_window_focus(verifier_setup):
    verifier, provider = verifier_setup
    # Set 1001 to foreground
    provider.set_foreground_window(1001)

    result = verifier.verify_window_focus(1001)
    assert result.verified is True

    result_wrong = verifier.verify_window_focus(1002)
    assert result_wrong.verified is False


def test_verify_clipboard_write(verifier_setup):
    verifier, provider = verifier_setup
    provider.write_clipboard("Expected secret text")

    result = verifier.verify_clipboard_write("Expected secret text")
    assert result.verified is True

    result_wrong = verifier.verify_clipboard_write("Different text")
    assert result_wrong.verified is False
