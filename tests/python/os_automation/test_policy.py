"""Tests for tool policy enforcement, risk tiers, and approval requirements."""

import pytest
from jarvis.os.manager import OSAutomationManager
from jarvis.os.models import MouseClickRequest
from jarvis.os.providers.mock import MockOSProvider
from jarvis.os.tools.registration import register_os_tools
from jarvis.tools.models import ApprovalMode, RiskLevel, ToolPermission, ToolRequest
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.registry import ToolRegistry


@pytest.fixture
def policy_setup(tmp_path):
    registry = ToolRegistry()
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)
    register_os_tools(registry, os_manager=os_mgr)
    profile = SecurityProfile()
    policy_engine = ToolPolicyEngine(default_profile=profile)
    return registry, os_mgr, policy_engine


def test_os_tools_registered_with_correct_permissions(policy_setup):
    registry, _, _ = policy_setup
    
    # Read-only screen capture
    screen_cap = registry.get("os.screen.capture")
    assert screen_cap is not None
    assert ToolPermission.READ in screen_cap.permissions
    assert screen_cap.risk_level == RiskLevel.LOW

    # Mouse action has EXECUTE permission
    mouse_click = registry.get("os.mouse.click")
    assert mouse_click is not None
    assert ToolPermission.EXECUTE in mouse_click.permissions
    assert mouse_click.risk_level == RiskLevel.MEDIUM

    # Read-only system info
    sys_tool = registry.get("os.system.info")
    assert sys_tool is not None
    assert ToolPermission.READ in sys_tool.permissions
    assert sys_tool.risk_level == RiskLevel.LOW


def test_destructive_click_policy_evaluation(policy_setup):
    registry, _, policy_engine = policy_setup
    tool_def = registry.get("os.mouse.click")

    profile = SecurityProfile(
        granted_permissions={ToolPermission.READ, ToolPermission.WRITE, ToolPermission.EXECUTE}
    )

    req = ToolRequest(
        tool_id="os.mouse.click",
        arguments={"clicks": 1, "is_destructive": False},
        caller="operator",
    )
    decision = policy_engine.evaluate(tool_def, req, caller_profile=profile)
    assert decision.allowed is True
    assert decision.risk_level == RiskLevel.MEDIUM
