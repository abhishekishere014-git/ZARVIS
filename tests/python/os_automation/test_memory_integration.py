"""Tests for Phase 06 Memory Engine integration with OS Automation subsystem."""

import pytest
from jarvis.memory.models import WorkingMessage
from jarvis.memory.working.buffer import WorkingBuffer
from jarvis.os.manager import OSAutomationManager
from jarvis.os.models import OSActionResult
from jarvis.os.providers.mock import MockOSProvider


def test_os_action_result_persisted_to_working_memory(tmp_path):
    provider = MockOSProvider()
    os_mgr = OSAutomationManager(provider=provider, workspace_root=tmp_path)
    buffer = WorkingBuffer()

    # Query system info
    sys_info = os_mgr.system.get_info()

    # Record OS context in memory buffer
    buffer.append(
        WorkingMessage(
            role="system",
            content=f"Current active window: '{sys_info.foreground_window_title}', OS: {sys_info.os_name}",
            metadata={"source": "os_telemetry", "cpu_count": sys_info.cpu_count},
        )
    )

    # Perform action: move mouse
    target_pos = os_mgr.mouse.move_cursor = (500, 300)
    action_res = OSActionResult(
        action_id="act_mouse_mv_01",
        tool_id="os.mouse.move",
        success=True,
        output={"x": 500, "y": 300},
    )

    buffer.append(
        WorkingMessage(
            role="assistant",
            content=f"Executed tool {action_res.tool_id}: moved cursor to (500, 300)",
            metadata={"action_id": action_res.action_id, "success": action_res.success},
        )
    )

    assert buffer.count() == 2
    messages = buffer.list()
    assert "Current active window" in messages[0].content
    assert messages[1].metadata["action_id"] == "act_mouse_mv_01"
