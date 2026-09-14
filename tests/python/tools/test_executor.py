"""Tests for supervised ToolExecutor pipeline and lifecycle events."""

import asyncio
from pathlib import Path
from typing import Optional
import pytest
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.tools.decorator import tool
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolPermission,
    ToolRequest,
)
from jarvis.tools.permissions import SecurityProfile
from jarvis.tools.policy import ToolPolicyEngine
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.sandbox import FileSystemSandbox


@pytest.mark.asyncio
async def test_tool_executor_successful_run(tmp_path: Path) -> None:
    registry = ToolRegistry()
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    bus = AsyncEventBus()
    await bus.start()

    received_events = []

    async def event_collector(evt: JarvisEvent) -> None:
        received_events.append(evt.type)

    bus.subscribe("*", event_collector)

    @tool(
        tool_id="test.greet",
        permissions={ToolPermission.READ},
    )
    async def greet(name: str, context: Optional[ToolExecutionContext] = None) -> str:
        assert context is not None
        assert context.workspace_dir == tmp_path.resolve()
        return f"Hello, {name}!"

    registry.register_tool(greet)

    executor = ToolExecutor(
        registry=registry,
        policy_engine=policy_engine,
        sandbox=sandbox,
        event_bus=bus,
    )

    req = ToolRequest(tool_id="test.greet", arguments={"name": "Alice"})
    result = await executor.execute(req)

    # Allow event bus to dispatch
    await asyncio.sleep(0.05)
    await bus.stop()

    assert result.is_success is True
    assert result.output == "Hello, Alice!"
    assert result.status == ToolExecutionStatus.SUCCESS

    # Verify event trail
    assert "tool.requested" in received_events
    assert "tool.authorized" in received_events
    assert "tool.started" in received_events
    assert "tool.completed" in received_events


@pytest.mark.asyncio
async def test_tool_executor_timeout_enforcement(tmp_path: Path) -> None:
    registry = ToolRegistry()
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)

    @tool(
        tool_id="test.slow",
        timeout_seconds=0.2,
    )
    async def slow_func() -> str:
        await asyncio.sleep(1.0)
        return "finished"

    registry.register_tool(slow_func)

    executor = ToolExecutor(
        registry=registry,
        policy_engine=policy_engine,
        sandbox=sandbox,
    )

    req = ToolRequest(tool_id="test.slow")
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.TIMEOUT
    assert "timed out" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_tool_executor_missing_tool_error(tmp_path: Path) -> None:
    registry = ToolRegistry()
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    req = ToolRequest(tool_id="nonexistent.tool")
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.FAILED
    assert "not registered" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_tool_executor_missing_arguments_error(tmp_path: Path) -> None:
    registry = ToolRegistry()
    sandbox = FileSystemSandbox(workspace_root=tmp_path)
    policy_engine = ToolPolicyEngine(sandbox=sandbox)

    @tool(tool_id="test.requires_arg")
    async def need_arg(target: str) -> str:
        return target

    registry.register_tool(need_arg)
    executor = ToolExecutor(registry=registry, policy_engine=policy_engine, sandbox=sandbox)

    req = ToolRequest(tool_id="test.requires_arg", arguments={})  # missing target
    result = await executor.execute(req)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.FAILED
    assert "Missing required arguments" in (result.error or "")
