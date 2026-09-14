"""Tests for screen capture and monitor enumeration subsystems."""

import pytest
from pathlib import Path
from jarvis.os.config import OSAutomationConfig
from jarvis.os.models import ScreenCaptureRequest
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.screen.capture import ScreenCaptureManager
from jarvis.os.screen.monitor import MonitorManager
from jarvis.os.security import OSSecurityManager


@pytest.fixture
def mock_screen_setup(tmp_path: Path):
    config = OSAutomationConfig(screens_temp_dir="temp/screens")
    provider = MockOSProvider(virtual_width=1920, virtual_height=1080)
    security = OSSecurityManager(workspace_root=tmp_path, screens_temp_dir="temp/screens")
    monitor_mgr = MonitorManager(provider=provider)
    capture_mgr = ScreenCaptureManager(provider=provider, security=security, config=config)
    return monitor_mgr, capture_mgr, provider


def test_monitor_enumeration(mock_screen_setup):
    monitor_mgr, _, provider = mock_screen_setup
    monitors = monitor_mgr.get_monitors()
    assert len(monitors) == 1
    assert monitors[0].width == 1920
    assert monitors[0].height == 1080
    assert monitors[0].is_primary is True

    screen_info = monitor_mgr.get_screen_info()
    assert screen_info.virtual_width == 1920
    assert screen_info.virtual_height == 1080


def test_screen_capture_full(mock_screen_setup):
    _, capture_mgr, _ = mock_screen_setup
    req = ScreenCaptureRequest(image_format="png", include_base64=True)
    res = capture_mgr.capture(req)

    assert res.width == 1920
    assert res.height == 1080
    assert res.format == "png"
    assert res.image_base64 is not None
    assert res.image_path is not None
    assert Path(res.image_path).name.startswith("screen_")


def test_screen_capture_region(mock_screen_setup):
    _, capture_mgr, _ = mock_screen_setup
    req = ScreenCaptureRequest(region=(100, 100, 300, 200), image_format="jpeg")
    res = capture_mgr.capture(req)

    assert res.width == 300
    assert res.height == 200
    assert res.format == "jpeg"


def test_screen_capture_downscale(mock_screen_setup):
    _, capture_mgr, _ = mock_screen_setup
    req = ScreenCaptureRequest(max_width=800, max_height=600)
    res = capture_mgr.capture(req)

    assert res.width <= 800
    assert res.height <= 600
