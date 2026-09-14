"""Tests for AIToolBridge translating Phase 03 ToolCalls into Phase 04 execution."""

import json
from pathlib import Path
import pytest
from jarvis.ai.models import Role, ToolCall
from jarvis.tools.builtins import register_builtin_tools
from jarvis.tools.factory import build_tool_system
from jarvis.tools.models import ToolExecutionStatus


@pytest.mark.asyncio
async def test_ai_bridge_executes_office_tool_call(tmp_path: Path) -> None:
    system = build_tool_system(workspace_dir=tmp_path)

    # Simulated AI model tool call
    ai_tool_call = ToolCall(
        id="call_998877",
        name="office.create_docx",
        arguments={
            "filename": "ai_generated_report.docx",
            "title": "Autonomous Strategy Document",
            "sections": [
                {"heading": "Introduction", "paragraph": "Generated autonomously by AI Agent."},
                {"heading": "Next Actions", "bullets": ["Deploy Phase 05", "Initialize tri-tier memory"]},
            ],
        },
    )

    result, chat_message = await system.bridge.execute_tool_call(
        tool_call=ai_tool_call,
        correlation_id="session_abc123",
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.is_success is True
    assert len(result.artifacts) == 1
    assert Path(result.artifacts[0]).exists()

    # Verify ChatMessage structure
    assert chat_message.role == Role.TOOL
    assert chat_message.tool_call_id == "call_998877"
    assert chat_message.name == "office.create_docx"

    parsed_content = json.loads(chat_message.content)
    assert parsed_content["status"] == "success"
    assert len(parsed_content["artifacts"]) == 1


@pytest.mark.asyncio
async def test_ai_bridge_handles_unknown_tool_safely(tmp_path: Path) -> None:
    system = build_tool_system(workspace_dir=tmp_path)

    bad_tool_call = ToolCall(
        id="call_000",
        name="nonexistent.delete_database",
        arguments={"all": True},
    )

    result, chat_message = await system.bridge.execute_tool_call(bad_tool_call)

    assert result.is_success is False
    assert result.status == ToolExecutionStatus.FAILED
    assert chat_message.role == Role.TOOL
    parsed = json.loads(chat_message.content)
    assert parsed["status"] == "failed"
    assert "not registered" in parsed["error"].lower()
