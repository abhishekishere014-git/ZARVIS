"""Deterministic security and permission policy engine for tool invocation."""

from typing import Any, Dict, Optional
from jarvis.tools.errors import SandboxViolationError
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolDefinition,
    ToolPolicyDecision,
    ToolRequest,
)
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.sandbox import FileSystemSandbox

PATH_ARGUMENT_KEYS = {"path", "filepath", "filename", "output_path", "destination", "target"}


class ToolPolicyEngine:
    """Evaluates whether a tool request is authorized under security profiles and sandbox rules."""

    def __init__(
        self,
        default_profile: Optional[SecurityProfile] = None,
        sandbox: Optional[FileSystemSandbox] = None,
    ) -> None:
        self.profile = default_profile or SecurityProfile()
        self.sandbox = sandbox

    def evaluate(
        self,
        tool_def: ToolDefinition,
        request: ToolRequest,
        caller_profile: Optional[SecurityProfile] = None,
    ) -> ToolPolicyDecision:
        """Determines whether a tool execution request is permitted.

        Returns:
            ToolPolicyDecision indicating authorization status, risk, and approval requirements.
        """
        active_profile = caller_profile or self.profile

        # 1. State check: is tool enabled?
        if not tool_def.enabled:
            return ToolPolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_def.id}' is currently disabled.",
                risk_level=tool_def.risk_level,
                permissions_required=tool_def.permissions,
            )

        # 2. Permission check: does caller possess all required permissions?
        if not active_profile.has_all_permissions(tool_def.permissions):
            missing = tool_def.permissions - active_profile.granted_permissions
            return ToolPolicyDecision(
                allowed=False,
                reason=f"Missing required permissions: {[p.value for p in missing]}",
                risk_level=tool_def.risk_level,
                permissions_required=tool_def.permissions,
            )

        # 3. Risk check: evaluate against caller risk tolerance and approval mode
        if tool_def.approval_mode == ApprovalMode.ALWAYS_DENY:
            return ToolPolicyDecision(
                allowed=False,
                reason=f"Execution of tool '{tool_def.id}' is permanently denied by policy.",
                risk_level=tool_def.risk_level,
                permissions_required=tool_def.permissions,
            )

        approval_needed = False
        if tool_def.approval_mode == ApprovalMode.USER_APPROVAL:
            approval_needed = True
        elif not active_profile.is_risk_acceptable(tool_def.risk_level):
            # Tool risk exceeds profile threshold - requires approval
            approval_needed = True

        # 4. Sandbox inspection: inspect path arguments if sandbox is configured
        if self.sandbox:
            for key, val in request.arguments.items():
                if key.lower() in PATH_ARGUMENT_KEYS and isinstance(val, str):
                    try:
                        # Test if path can be safely resolved within sandbox
                        self.sandbox.resolve_safe_path(val)
                    except SandboxViolationError as exc:
                        return ToolPolicyDecision(
                            allowed=False,
                            reason=f"Sandbox boundary violation on parameter '{key}': {exc}",
                            risk_level=tool_def.risk_level,
                            permissions_required=tool_def.permissions,
                        )

        return ToolPolicyDecision(
            allowed=True,
            approval_required=approval_needed,
            reason="Tool invocation authorized under current security policy.",
            risk_level=tool_def.risk_level,
            permissions_required=tool_def.permissions,
        )
