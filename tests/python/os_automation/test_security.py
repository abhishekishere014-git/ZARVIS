"""Tests for OS security boundaries, coordinate bounds, key allowlists, and secret redaction."""

import pytest
from pathlib import Path
from jarvis.os.errors import OSSecurityError
from jarvis.os.models import CoordinateSpace, MonitorInfo, Rect2D, ScreenInfo, WindowInfo
from jarvis.os.security import OSSecurityManager


@pytest.fixture
def security_mgr(tmp_path):
    return OSSecurityManager(workspace_root=tmp_path, screens_temp_dir="temp/screens")


def test_screen_coordinate_validation_in_bounds(security_mgr):
    screen_info = ScreenInfo(
        virtual_x=0,
        virtual_y=0,
        virtual_width=1920,
        virtual_height=1080,
    )
    x, y = security_mgr.validate_coordinates(500, 500, screen_info, CoordinateSpace.SCREEN)
    assert (x, y) == (500, 500)


def test_screen_coordinate_validation_out_of_bounds(security_mgr):
    screen_info = ScreenInfo(
        virtual_x=0,
        virtual_y=0,
        virtual_width=1920,
        virtual_height=1080,
    )
    with pytest.raises(OSSecurityError):
        security_mgr.validate_coordinates(-10, 500, screen_info, CoordinateSpace.SCREEN)

    with pytest.raises(OSSecurityError):
        security_mgr.validate_coordinates(2000, 500, screen_info, CoordinateSpace.SCREEN)

    with pytest.raises(OSSecurityError):
        security_mgr.validate_coordinates(500, 1200, screen_info, CoordinateSpace.SCREEN)


def test_window_coordinate_validation(security_mgr):
    screen_info = ScreenInfo(virtual_x=0, virtual_y=0, virtual_width=1920, virtual_height=1080)
    target_window = WindowInfo(
        handle_id=1001,
        title="App",
        x=200,
        y=150,
        width=400,
        height=300,
    )
    # Coordinate (50, 50) inside window maps to screen (250, 200)
    screen_x, screen_y = security_mgr.validate_coordinates(
        x=50,
        y=50,
        screen_info=screen_info,
        coordinate_space=CoordinateSpace.WINDOW,
        target_window=target_window,
    )
    assert screen_x == 250
    assert screen_y == 200

    # Outside window client bounds
    with pytest.raises(OSSecurityError):
        security_mgr.validate_coordinates(
            x=500,
            y=50,
            screen_info=screen_info,
            coordinate_space=CoordinateSpace.WINDOW,
            target_window=target_window,
        )


def test_key_allowlist_validation(security_mgr):
    assert security_mgr.validate_key("ENTER") == "ENTER"
    assert security_mgr.validate_key("a") == "a"
    assert security_mgr.validate_key("F5") == "F5"

    with pytest.raises(OSSecurityError):
        security_mgr.validate_key("MALICIOUS_KEY_CODE_EXEC")


def test_hotkey_sequence_validation(security_mgr):
    assert security_mgr.validate_hotkey_sequence(["CTRL", "C"]) == ["CTRL", "C"]
    assert security_mgr.validate_hotkey_sequence(["ALT", "TAB"]) == ["ALT", "TAB"]

    with pytest.raises(OSSecurityError):
        security_mgr.validate_hotkey_sequence(["CTRL"])  # min length is 2

    with pytest.raises(OSSecurityError):
        security_mgr.validate_hotkey_sequence(["CTRL", "ALT", "SHIFT", "WIN", "EXTRA"])  # max length is 4


def test_sensitive_text_detection(security_mgr):
    assert security_mgr.is_sensitive_text("sk-ant-api03-abcdefghijklmnopqrstu") is True
    assert security_mgr.is_sensitive_text("ghp_123456789012345678901234567890123456") is True
    assert security_mgr.is_sensitive_text("password: MySuperSecretPassword123") is True
    assert security_mgr.is_sensitive_text("Hello world, this is a harmless message") is False


def test_redact_sensitive_text(security_mgr):
    redacted = security_mgr.redact_sensitive_text("sk-ant-api03-abcdefghijklmnopqrstu")
    assert "[REDACTED_SECRET]" in redacted
    assert "sk-ant" not in redacted


def test_safe_screenshot_path_traversal_prevention(security_mgr):
    with pytest.raises(OSSecurityError):
        security_mgr.resolve_safe_screenshot_path("../../escaped.png")

    with pytest.raises(OSSecurityError):
        security_mgr.resolve_safe_screenshot_path("/etc/passwd")

    safe_path = security_mgr.resolve_safe_screenshot_path("screen_123.png")
    assert str(safe_path).startswith(str(security_mgr.temp_dir))
