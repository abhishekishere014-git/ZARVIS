"""Tests for normalized Tool data models and contracts."""

import pytest
from pydantic import ValidationError
from jarvis.tools.models import (
    ApprovalMode,
    RiskLevel,
    ToolDefinition,
    ToolExecutionStatus,
    ToolPermission,
    ToolRequest,
    ToolResult,
)


def test_tool_definition_defaults_and_validation() -> None:
    tool_def = ToolDefinition(
        id="test.tool",
        name="Test Tool",
        description="A test tool definition",
        input_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
    )
    assert tool_def.id == "test.tool"
    assert tool_def.version == "1.0.0"
    assert tool_def.category == "general"
    assert tool_def.risk_level == RiskLevel.LOW
    assert tool_def.approval_mode == ApprovalMode.AUTO_APPROVE
    assert tool_def.enabled is True
    assert tool_def.permissions == set()


def test_tool_request_execution_id_generation() -> None:
    req1 = ToolRequest(tool_id="test.tool")
    req2 = ToolRequest(tool_id="test.tool")
    assert req1.execution_id != req2.execution_id
    assert req1.tool_id == "test.tool"
    assert req1.caller == "agent"


def test_tool_result_status_and_artifacts() -> None:
    res = ToolResult(
        execution_id="exec_1",
        tool_id="test.tool",
        status=ToolExecutionStatus.SUCCESS,
        output={"key": "val"},
        artifacts=["/path/to/file.docx"],
    )
    assert res.is_success is True
    assert res.artifacts == ["/path/to/file.docx"]

    res_fail = ToolResult(
        execution_id="exec_2",
        tool_id="test.tool",
        status=ToolExecutionStatus.FAILED,
        error="Something broke",
    )
    assert res_fail.is_success is False
    assert res_fail.error == "Something broke"


def test_tool_definition_invalid_timeout() -> None:
    with pytest.raises(ValidationError):
        ToolDefinition(
            id="bad.tool",
            name="Bad",
            description="Invalid timeout",
            timeout_seconds=0.05,  # Min is 0.1
        )
