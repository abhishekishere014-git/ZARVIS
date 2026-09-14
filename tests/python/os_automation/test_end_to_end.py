"""End-to-end integration test validating full desktop automation flow."""

import pytest
import asyncio
from jarvis.core.bus import AsyncEventBus
from jarvis.os.manager import OSAutomationManager
from jarvis.os.models import (
    ClipboardReadRequest,
    ClipboardWriteRequest,
    CoordinateSpace,
    KeyboardTypeRequest,
    MouseButton,
    MouseClickRequest,
    MouseMoveRequest,
    ScreenCaptureRequest,
    WindowQuery,
)
from jarvis.os.providers.mock import MockOSProvider
from jarvis.protocol.models import JarvisEvent


@pytest.mark.asyncio
async def test_full_os_automation_end_to_end_flow(tmp_path):
    # 1. Initialize EventBus and OS Automation Manager
    bus = AsyncEventBus()
    await bus.start()

    events_received = []
    async def track_events(evt: JarvisEvent):
        events_received.append(evt)

    bus.subscribe("*", track_events)

    provider = MockOSProvider()
    os_mgr = OSAutomationManager(
        provider=provider,
        event_bus=bus,
        workspace_root=tmp_path,
    )

    # 2. Query system info
    sys_info = os_mgr.system.get_info()
    assert "Windows" in sys_info.os_name

    # 3. Find and focus target window
    notepad_win = os_mgr.window.find_window(WindowQuery(title="Notepad - Untitled"))
    assert notepad_win.handle_id == 1002
    assert os_mgr.window.focus_window(notepad_win.handle_id) is True

    # 4. Capture screen before action
    pre_capture = os_mgr.screen.capture(ScreenCaptureRequest(image_format="png"))
    assert pre_capture.width == 1920
    await os_mgr.emit_event("os.screen.captured", "corr_e2e_1", {"image_path": pre_capture.image_path})

    # 5. Move mouse relative to window coordinate space
    move_req = MouseMoveRequest(
        x=50,
        y=50,
        coordinate_space=CoordinateSpace.WINDOW,
        window_id=notepad_win.handle_id,
    )
    # Notepad is at (650, 150), so (50, 50) inside maps to (700, 200)
    tx, ty = os_mgr.mouse.move(move_req, target_window=notepad_win)
    assert (tx, ty) == (700, 200)
    assert (provider.cursor_x, provider.cursor_y) == (700, 200)

    # 6. Click inside window
    click_req = MouseClickRequest(button=MouseButton.LEFT, clicks=1)
    os_mgr.mouse.click(click_req)
    await os_mgr.emit_event("os.mouse.clicked", "corr_e2e_2", {"button": "LEFT", "x": tx, "y": ty})

    # 7. Type text into window
    type_req = KeyboardTypeRequest(text="Hello from automated JARVIS session!")
    chars_typed = os_mgr.keyboard.type_text(type_req)
    assert chars_typed == len("Hello from automated JARVIS session!")
    await os_mgr.emit_event("os.keyboard.typed", "corr_e2e_3", {"chars": chars_typed})

    # 8. Set and read clipboard
    os_mgr.clipboard.write(ClipboardWriteRequest(text="Synthesized payload text"))
    clip_res = os_mgr.clipboard.read(ClipboardReadRequest())
    assert clip_res.text == "Synthesized payload text"
    await os_mgr.emit_event("os.clipboard.modified", "corr_e2e_4", {"length": clip_res.length})

    # 9. Verify post-execution state
    focus_ver = os_mgr.verifier.verify_window_focus(notepad_win.handle_id)
    assert focus_ver.verified is True

    pos_ver = os_mgr.verifier.verify_mouse_position(700, 200)
    assert pos_ver.verified is True

    clip_ver = os_mgr.verifier.verify_clipboard_write("Synthesized payload text")
    assert clip_ver.verified is True

    # 10. Confirm telemetry events
    await asyncio.sleep(0.05)
    await bus.stop()

    assert len(events_received) == 4
    event_types = [e.type for e in events_received]
    assert "os.screen.captured" in event_types
    assert "os.mouse.clicked" in event_types
    assert "os.keyboard.typed" in event_types
    assert "os.clipboard.modified" in event_types
