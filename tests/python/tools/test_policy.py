"""Tests for ToolPolicyEngine permission checks, risk levels, and sandbox inspection."""

from pathlib import Path
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolDefinition,
    ToolPermission,
    ToolRequest,
)
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.sandbox import FileSystemSandbox


def test_policy_allows_safe_operation() -> None:
    engine = ToolPolicyEngine()
    tool_def = ToolDefinition(
        id="safe.tool",
        name="Safe Tool",
        description="Safe",
        permissions={ToolPermission.READ},
        risk_level=RiskLevel.LOW,
    )
    req = ToolRequest(tool_id="safe.tool")
    decision = engine.evaluate(tool_def, req)

    assert decision.allowed is True
    assert decision.approval_required is False


def test_policy_rejects_disabled_tool() -> None:
    engine = ToolPolicyEngine()
    tool_def = ToolDefinition(
        id="disabled.tool",
        name="Disabled",
        description="Disabled",
        enabled=False,
    )
    req = ToolRequest(tool_id="disabled.tool")
    decision = engine.evaluate(tool_def, req)

    assert decision.allowed is False
    assert "disabled" in decision.reason.lower()


def test_policy_rejects_missing_permission() -> None:
    # Caller only has READ
    profile = SecurityProfile(granted_permissions={ToolPermission.READ})
    engine = ToolPolicyEngine(default_profile=profile)

    # Tool requires WRITE
    tool_def = ToolDefinition(
        id="write.tool",
        name="Writer",
        description="Writes",
        permissions={ToolPermission.WRITE},
    )
    req = ToolRequest(tool_id="write.tool")
    decision = engine.evaluate(tool_def, req)

    assert decision.allowed is False
    assert "missing required permissions" in decision.reason.lower()


def test_policy_detects_user_approval_requirement() -> None:
    profile = SecurityProfile(max_risk_level=RiskLevel.LOW)
    engine = ToolPolicyEngine(default_profile=profile)

    # High risk tool
    tool_def = ToolDefinition(
        id="high_risk.tool",
        name="High Risk",
        description="Danger",
        risk_level=RiskLevel.HIGH,
    )
    req = ToolRequest(tool_id="high_risk.tool")
    decision = engine.evaluate(tool_def, req)

    assert decision.allowed is True
    assert decision.approval_required is True


def test_policy_blocks_always_deny_tools() -> None:
    engine = ToolPolicyEngine()
    tool_def = ToolDefinition(
        id="forbidden.tool",
        name="Forbidden",
        description="Forbidden",
        approval_mode=ApprovalMode.ALWAYS_DENY,
    )
    req = ToolRequest(tool_id="forbidden.tool")
    decision = engine.evaluate(tool_def, req)

    assert decision.allowed is False
    assert "permanently denied" in decision.reason.lower()


def test_policy_catches_sandbox_violation_in_arguments(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    engine = ToolPolicyEngine(sandbox=sandbox)

    tool_def = ToolDefinition(
        id="file.tool",
        name="File Tool",
        description="File",
        permissions={ToolPermission.WRITE},
    )
    req = ToolRequest(tool_id="file.tool", arguments={"filename": "../../escape.txt"})
    decision = engine.evaluate(tool_def, req)

    assert decision.allowed is False
    assert "sandbox boundary violation" in decision.reason.lower()
