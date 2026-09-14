"""Tests for system telemetry and read-only host inspection."""

import pytest
from jarvis.os.models import SystemInfo
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.system.info import SystemInfoManager


@pytest.fixture
def system_setup():
    provider = MockOSProvider()
    sys_mgr = SystemInfoManager(provider=provider)
    return sys_mgr, provider


def test_system_info_fields(system_setup):
    sys_mgr, _ = system_setup
    info = sys_mgr.get_info()

    assert isinstance(info, SystemInfo)
    assert "Windows" in info.os_name
    assert info.cpu_count >= 1
    assert info.memory_total_bytes > 0
    assert info.architecture != ""
    assert info.foreground_window_title is not None
