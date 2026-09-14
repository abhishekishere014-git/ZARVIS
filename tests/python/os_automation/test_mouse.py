"""Tests for mouse movement, clicking, and scrolling input subsystems."""

import pytest
from jarvis.os.errors import OSSecurityError
from jarvis.os.input.mouse import MouseManager
from jarvis.os.models import CoordinateSpace, MouseButton, MouseClickRequest, MouseMoveRequest, MouseScrollRequest
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.security import OSSecurityManager


@pytest.fixture
def mouse_setup(tmp_path):
    provider = MockOSProvider(screen_width=1920, screen_height=1080)
    security = OSSecurityManager(workspace_root=tmp_path, screens_temp_dir="temp/screens")
    mouse_mgr = MouseManager(provider=provider, security=security)
    return mouse_mgr, provider


def test_mouse_move_screen_space(mouse_setup):
    mouse_mgr, provider = mouse_setup
    req = MouseMoveRequest(x=500, y=400, coordinate_space=CoordinateSpace.SCREEN)
    res = mouse_mgr.move(req)

    assert res == (500, 400)
    assert provider.cursor_x == 500
    assert provider.cursor_y == 400


def test_mouse_move_out_of_bounds_rejected(mouse_setup):
    mouse_mgr, provider = mouse_setup
    req = MouseMoveRequest(x=9999, y=9999, coordinate_space=CoordinateSpace.SCREEN)
    with pytest.raises(OSSecurityError):
        mouse_mgr.move(req)


def test_mouse_click_single_left(mouse_setup):
    mouse_mgr, provider = mouse_setup
    req = MouseClickRequest(x=250, y=350, button=MouseButton.LEFT, clicks=1)
    res = mouse_mgr.click(req)

    assert res == (250, 350)
    assert provider.cursor_x == 250
    assert provider.cursor_y == 350
    assert len(provider.click_history) == 1
    assert provider.click_history[0] == (MouseButton.LEFT, 1, 250, 350)


def test_mouse_click_double_and_right(mouse_setup):
    mouse_mgr, provider = mouse_setup
    req_double = MouseClickRequest(x=300, y=300, button=MouseButton.LEFT, clicks=2)
    mouse_mgr.click(req_double)

    req_right = MouseClickRequest(x=400, y=400, button=MouseButton.RIGHT, clicks=1)
    mouse_mgr.click(req_right)

    assert len(provider.click_history) == 2
    assert provider.click_history[0] == (MouseButton.LEFT, 2, 300, 300)
    assert provider.click_history[1] == (MouseButton.RIGHT, 1, 400, 400)


def test_mouse_scroll(mouse_setup):
    mouse_mgr, provider = mouse_setup
    req = MouseScrollRequest(clicks=5, x=100, y=100)
    res = mouse_mgr.scroll(req)

    assert res == 5
    assert len(provider.scroll_history) == 1
    assert provider.scroll_history[0] == 5
