"""Integration tests for Phase 05 Multi-Agent Runtime invoking Phase 09 Vision tools."""

from pathlib import Path
import pytest
from jarvis.tools.factory import build_tool_system
from jarvis.tools.models import ToolPermission, ToolRequest
from jarvis.tools.permissions import SecurityProfile
from jarvis.vision.manager import VisionManager
from jarvis.vision.providers.mock import MockVisionProvider
from jarvis.vision.tools.registration import register_vision_tools


@pytest.fixture
def agent_profile():
    return SecurityProfile(
        granted_permissions={ToolPermission.READ, ToolPermission.WRITE, ToolPermission.EXECUTE}
    )


@pytest.mark.asyncio
async def test_agent_invokes_vision_screen_analyze(tmp_path: Path, agent_profile):
    tool_system = build_tool_system(workspace_dir=tmp_path, security_profile=agent_profile)
    provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=provider)
    register_vision_tools(tool_system.registry, vision_manager=vision_mgr)

    req = ToolRequest(
        tool_id="vision.screen.analyze",
        arguments={"monitor_id": 0, "force_refresh": True},
        caller="agent_orchestrator",
    )

    result = await tool_system.executor.execute(req, caller_profile=agent_profile)
    assert result.is_success is True
    assert result.output["success"] is True
    assert result.output["element_count"] > 0


@pytest.mark.asyncio
async def test_agent_invokes_vision_element_find(tmp_path: Path, agent_profile):
    tool_system = build_tool_system(workspace_dir=tmp_path, security_profile=agent_profile)
    provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=provider)
    register_vision_tools(tool_system.registry, vision_manager=vision_mgr)

    req = ToolRequest(
        tool_id="vision.element.find",
        arguments={"query": "Google Search", "monitor_id": 0},
        caller="agent_orchestrator",
    )

    result = await tool_system.executor.execute(req, caller_profile=agent_profile)
    assert result.is_success is True
    assert result.output["match_count"] >= 1


@pytest.mark.asyncio
async def test_agent_invokes_vision_target_resolve(tmp_path: Path, agent_profile):
    tool_system = build_tool_system(workspace_dir=tmp_path, security_profile=agent_profile)
    provider = MockVisionProvider()
    vision_mgr = VisionManager(provider=provider)
    register_vision_tools(tool_system.registry, vision_manager=vision_mgr)

    req = ToolRequest(
        tool_id="vision.target.resolve",
        arguments={"query": "Google Search", "monitor_id": 0},
        caller="agent_orchestrator",
    )

    result = await tool_system.executor.execute(req, caller_profile=agent_profile)
    assert result.is_success is True
    assert result.output["success"] is True
    assert "target_point" in result.output
    assert result.output["confidence"] >= 0.85
