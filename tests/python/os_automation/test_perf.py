"""Performance benchmarks for OS Automation operations ensuring sub-second response times."""

import pytest
import time
from jarvis.os.manager import OSAutomationManager
from jarvis.os.models import ClipboardWriteRequest, MouseMoveRequest, ScreenCaptureRequest
from jarvis.os.providers.mock import MockOSProvider


@pytest.fixture
def perf_setup(tmp_path):
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)
    return os_mgr


def test_mouse_move_latency(perf_setup):
    os_mgr = perf_setup
    req = MouseMoveRequest(x=400, y=300)

    start = time.perf_counter()
    os_mgr.mouse.move(req)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 50.0  # Quality Gate: Mouse move latency < 50ms


def test_window_list_latency(perf_setup):
    os_mgr = perf_setup

    start = time.perf_counter()
    windows = os_mgr.window.list_windows()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 100.0  # Quality Gate: Window listing < 100ms
    assert len(windows) >= 2


def test_screen_capture_latency(perf_setup):
    os_mgr = perf_setup
    req = ScreenCaptureRequest(image_format="png")

    start = time.perf_counter()
    res = os_mgr.screen.capture(req)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 300.0  # Quality Gate: Screen capture < 300ms
    assert res.width == 1920


def test_clipboard_write_and_read_latency(perf_setup):
    os_mgr = perf_setup
    w_req = ClipboardWriteRequest(text="Performance latency benchmark payload")

    start_write = time.perf_counter()
    os_mgr.clipboard.write(w_req)
    write_ms = (time.perf_counter() - start_write) * 1000
    assert write_ms < 50.0

    start_read = time.perf_counter()
    r_res = os_mgr.clipboard.read()
    read_ms = (time.perf_counter() - start_read) * 1000
    assert read_ms < 50.0
    assert r_res.text == "Performance latency benchmark payload"


def test_system_info_latency(perf_setup):
    os_mgr = perf_setup

    start = time.perf_counter()
    info = os_mgr.system.get_info()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 50.0
    assert info.cpu_count >= 1
