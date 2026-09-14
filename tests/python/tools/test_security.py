"""Security, boundary violation, and adversarial attack test suite."""

from pathlib import Path
import pytest
from jarvis.tools.decorator import tool
from jarvis.tools.errors import SandboxViolationError
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolExecutionStatus,
    ToolPermission,
    ToolRequest,
)
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.sandbox import FileSystemSandbox


@pytest.mark.asyncio
async def test_security_blocks_relative_traversal_attack(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    registry = ToolRegistry()

    @tool(tool_id="test.writer", permissions={ToolPermission.WRITE})
    async def writer_func(filename: str) -> str:
        return filename

    registry.register_tool(writer_func)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    # Attempt traversal in argument
    req = ToolRequest(tool_id="test.writer", arguments={"filename": "../../../Windows/System32/evil.dll"})
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.DENIED
    assert "sandbox boundary violation" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_security_blocks_absolute_path_escape(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    registry = ToolRegistry()

    @tool(tool_id="test.writer", permissions={ToolPermission.WRITE})
    async def writer_func(filename: str) -> str:
        return filename

    registry.register_tool(writer_func)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    req = ToolRequest(tool_id="test.writer", arguments={"filename": "C:/Windows/win.ini"})
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.DENIED


@pytest.mark.asyncio
async def test_security_blocks_unauthorized_permission_escalation(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    # Caller has only READ permission
    restricted_profile = SecurityProfile(granted_permissions={ToolPermission.READ})
    policy_engine = ToolPolicyEngine(default_profile=restricted_profile, sandbox=sandbox)
    registry = ToolRegistry()

    @tool(tool_id="test.privileged", permissions={ToolPermission.SYSTEM, ToolPermission.EXECUTE})
    async def privileged_func() -> str:
        return "root"

    registry.register_tool(privileged_func)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    req = ToolRequest(tool_id="test.privileged")
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.DENIED
    assert "missing required permissions" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_security_blocks_disabled_tool(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    registry = ToolRegistry()

    @tool(tool_id="test.disabled")
    async def disabled_func() -> str:
        return "ok"

    registry.register_tool(disabled_func)
    registry.disable("test.disabled")

    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)
    req = ToolRequest(tool_id="test.disabled")
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.DENIED
    assert "disabled" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_security_blocks_always_deny_tool(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    registry = ToolRegistry()

    @tool(tool_id="test.forbidden", approval_mode=ApprovalMode.ALWAYS_DENY)
    async def forbidden_func() -> str:
        return "ok"

    registry.register_tool(forbidden_func)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    req = ToolRequest(tool_id="test.forbidden")
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.DENIED
    assert "permanently denied" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_security_scrubs_secrets_from_error_traces(tmp_path: Path) -> None:
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    registry = ToolRegistry()

    @tool(tool_id="test.failing")
    async def leaking_func(secret_key: str) -> str:
        raise ValueError(f"Failed with key: {secret_key}")

    registry.register_tool(leaking_func)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    req = ToolRequest(
        tool_id="test.failing",
        arguments={"secret_key": "sk-1234567890abcdef1234567890abcdef"},
    )
    result = await executor.execute(req)

    assert result.is_success is False
    # Audit log should be scrubbed
    audit_event = executor.audit_logger.recent_records[-1]
    assert "sk-1234567890abcdef1234567890abcdef" not in str(audit_event.arguments_summary)
    assert "[REDACTED_SECRET]" in str(audit_event.arguments_summary)
