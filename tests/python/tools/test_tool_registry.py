"""Tests for ToolRegistry registration, discovery, and filtering."""

import pytest
from jarvis.tools.decorator import tool
from jarvis.tools.errors import DuplicateToolError, ToolNotFoundError
from jarvis.tools.models import (
    RiskLevel,
    ToolDefinition,
    ToolPermission,
)
from jarvis.tools.registry import ToolRegistry


def test_tool_registry_registration_and_get() -> None:
    registry = ToolRegistry()

    tool_def = ToolDefinition(
        id="sample.echo",
        name="Echo",
        description="Echo input",
        category="utility",
        permissions={ToolPermission.READ},
        risk_level=RiskLevel.LOW,
    )

    async def echo_handler(text: str) -> str:
        return text

    registry.register(tool_def, echo_handler)
    assert registry.has("sample.echo") is True

    retrieved = registry.get("sample.echo")
    assert retrieved.id == "sample.echo"
    assert registry.get_handler("sample.echo") is echo_handler

    # Duplicate registration must fail
    with pytest.raises(DuplicateToolError):
        registry.register(tool_def, echo_handler)


def test_tool_registry_unregister() -> None:
    registry = ToolRegistry()
    tool_def = ToolDefinition(id="temp.tool", name="Temp", description="Temporary")
    registry.register(tool_def, lambda: None)

    assert registry.unregister("temp.tool") is True
    assert registry.has("temp.tool") is False
    assert registry.unregister("temp.tool") is False

    with pytest.raises(ToolNotFoundError):
        registry.get("temp.tool")


def test_tool_registry_decorator_registration_and_filtering() -> None:
    registry = ToolRegistry()

    @tool(tool_id="office.sample", category="office", risk_level=RiskLevel.LOW, permissions={ToolPermission.WRITE})
    async def sample_office() -> str:
        return "doc"

    @tool(tool_id="sys.exec", category="system", risk_level=RiskLevel.CRITICAL, permissions={ToolPermission.EXECUTE})
    async def sample_sys() -> str:
        return "sys"

    registry.register_tool(sample_office)
    registry.register_tool(sample_sys)

    # Filter by category
    office_tools = registry.list(category="office")
    assert len(office_tools) == 1
    assert office_tools[0].id == "office.sample"

    # Discovery by risk
    safe_tools = registry.discover(max_risk_level=RiskLevel.MEDIUM)
    assert len(safe_tools) == 1
    assert safe_tools[0].id == "office.sample"

    # Discovery by permission
    write_tools = registry.discover(required_permission=ToolPermission.WRITE)
    assert len(write_tools) == 1
    assert write_tools[0].id == "office.sample"


def test_tool_enable_disable() -> None:
    registry = ToolRegistry()
    tool_def = ToolDefinition(id="toggle.tool", name="Toggle", description="Toggleable")
    registry.register(tool_def, lambda: None)

    assert registry.get("toggle.tool").enabled is True
    registry.disable("toggle.tool")
    assert registry.get("toggle.tool").enabled is False
    assert len(registry.list(enabled_only=True)) == 0
    assert len(registry.list(enabled_only=False)) == 1

    registry.enable("toggle.tool")
    assert registry.get("toggle.tool").enabled is True
