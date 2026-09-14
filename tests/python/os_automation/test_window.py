"""Tests for desktop application window enumeration, resolution, and state control."""

import pytest
from jarvis.os.errors import WindowAmbiguityError, WindowNotFoundError
from jarvis.os.models import WindowAction, WindowInfo, WindowQuery
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.window.manager import WindowManager


@pytest.fixture
def window_setup():
    provider = MockOSProvider()
    # MockOSProvider has windows: 1001 (Calculator), 1002 (Untitled - Notepad), 1003 (Document - WordPad)
    window_mgr = WindowManager(provider=provider)
    return window_mgr, provider


def test_window_list(window_setup):
    window_mgr, _ = window_setup
    windows = window_mgr.list_windows()
    assert len(windows) >= 2
    titles = [w.title for w in windows]
    assert "Calculator" in titles
    assert "Notepad - Untitled" in titles


def test_window_find_unique(window_setup):
    window_mgr, _ = window_setup
    # Find by title
    calc = window_mgr.find_window(WindowQuery(title="Calculator"))
    assert calc.handle_id == 1001
    assert calc.process_name == "calculator.exe"

    # Find by process
    notepad = window_mgr.find_window(WindowQuery(process_name="notepad.exe"))
    assert notepad.handle_id == 1002


def test_window_find_not_found(window_setup):
    window_mgr, _ = window_setup
    with pytest.raises(WindowNotFoundError):
        window_mgr.find_window(WindowQuery(title="Nonexistent Application Window XYZ"))


def test_window_find_ambiguity_raises_error(window_setup):
    window_mgr, provider = window_setup
    # Inject a duplicate calculator window
    provider.windows[1004] = WindowInfo(
        handle_id=1004,
        title="Calculator Secondary",
        process_name="calculator.exe",
        process_id=4521,
    )

    with pytest.raises(WindowAmbiguityError) as exc_info:
        window_mgr.find_window(WindowQuery(title="Calculator"))

    assert "Ambiguous resolution prohibited" in str(exc_info.value)


def test_window_state_transitions(window_setup):
    window_mgr, provider = window_setup
    handle = 1001

    # Focus
    assert window_mgr.focus_window(handle) is True
    fg = window_mgr.get_foreground_window()
    assert fg is not None
    assert fg.handle_id == handle

    # Minimize
    assert window_mgr.minimize_window(handle) is True
    assert provider.windows[handle].is_minimized is True

    # Maximize
    assert window_mgr.maximize_window(handle) is True
    assert provider.windows[handle].is_maximized is True
    assert provider.windows[handle].is_minimized is False

    # Restore
    assert window_mgr.restore_window(handle) is True
    assert provider.windows[handle].is_maximized is False
    assert provider.windows[handle].is_minimized is False
