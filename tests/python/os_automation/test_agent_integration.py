"""Tests for Phase 05 Multi-Agent Runtime integration with Phase 08 OS Automation tools."""

import pytest
from pathlib import Path
from jarvis.os.manager import OSAutomationManager
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.tools.registration import register_os_tools
from jarvis.tools.factory import build_tool_system
from jarvis.tools.models import ToolPermission, ToolRequest
from jarvis.tools.permissions import SecurityProfile


@pytest.fixture
def agent_profile():
    return SecurityProfile(
        granted_permissions={ToolPermission.READ, ToolPermission.WRITE, ToolPermission.EXECUTE}
    )


@pytest.mark.asyncio
async def test_agent_invokes_os_system_info_via_executor(tmp_path: Path, agent_profile):
    tool_system = build_tool_system(workspace_dir=tmp_path, security_profile=agent_profile)
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)
    register_os_tools(tool_system.registry, os_manager=os_mgr)

    req = ToolRequest(
        tool_id="os.system.info",
        arguments={},
        caller="agent_orchestrator",
    )

    result = await tool_system.executor.execute(req, caller_profile=agent_profile)
    assert result.is_success is True
    assert "Windows" in result.output["os_name"]
    assert result.output["cpu_count"] >= 1


@pytest.mark.asyncio
async def test_agent_invokes_os_window_list_via_executor(tmp_path: Path, agent_profile):
    tool_system = build_tool_system(workspace_dir=tmp_path, security_profile=agent_profile)
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)
    register_os_tools(tool_system.registry, os_manager=os_mgr)

    req = ToolRequest(
        tool_id="os.window.list",
        arguments={},
        caller="agent_orchestrator",
    )

    result = await tool_system.executor.execute(req, caller_profile=agent_profile)
    assert result.is_success is True
    assert len(result.output) >= 2


@pytest.mark.asyncio
async def test_agent_invokes_os_mouse_move_via_executor(tmp_path: Path, agent_profile):
    tool_system = build_tool_system(workspace_dir=tmp_path, security_profile=agent_profile)
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)
    register_os_tools(tool_system.registry, os_manager=os_mgr)

    req = ToolRequest(
        tool_id="os.mouse.move",
        arguments={"x": 350, "y": 250},
        caller="agent_orchestrator",
    )

    result = await tool_system.executor.execute(req, caller_profile=agent_profile)
    assert result.is_success is True
    assert provider.cursor_x == 350
    assert provider.cursor_y == 250
