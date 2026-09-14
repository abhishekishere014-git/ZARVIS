"""Tests for ToolRegistry registration, schema export, and metadata compliance."""

import pytest
from jarvis.os.manager import OSAutomationManager
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.tools.registration import ALL_OS_TOOLS, register_os_tools
from jarvis.tools.models import RiskLevel, ToolPermission
from jarvis.tools.registry import ToolRegistry


@pytest.fixture
def registry_setup(tmp_path):
    registry = ToolRegistry()
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)
    register_os_tools(registry, os_manager=os_mgr)
    return registry, os_mgr


def test_all_twenty_tools_registered(registry_setup):
    registry, _ = registry_setup
    registered = registry.list()
    assert len(registered) == 20
    assert len(ALL_OS_TOOLS) == 20


def test_expected_tool_ids_present(registry_setup):
    registry, _ = registry_setup
    expected_tool_ids = [
        "os.screen.capture",
        "os.screen.monitors",
        "os.screen.info",
        "os.mouse.move",
        "os.mouse.click",
        "os.mouse.double_click",
        "os.mouse.right_click",
        "os.mouse.scroll",
        "os.keyboard.type",
        "os.keyboard.press",
        "os.keyboard.hotkey",
        "os.window.list",
        "os.window.focus",
        "os.window.minimize",
        "os.window.maximize",
        "os.window.restore",
        "os.clipboard.read",
        "os.clipboard.write",
        "os.clipboard.clear",
        "os.system.info",
    ]
    for tid in expected_tool_ids:
        assert registry.has(tid), f"Tool {tid} must be present in registry"


def test_export_ai_tool_definitions(registry_setup):
    registry, _ = registry_setup
    definitions = registry.export_ai_tool_definitions()
    assert len(definitions) == 20
    for defn in definitions:
        assert hasattr(defn, "name") and defn.name
        assert hasattr(defn, "description")
        assert hasattr(defn, "parameters") or hasattr(defn, "input_schema")
