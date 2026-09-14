"""Unit tests for Phase 08 OS Automation domain models and contracts."""

import pytest
from pydantic import ValidationError
from jarvis.os.models import (
    ClipboardClearRequest,
    ClipboardData,
    ClipboardFormat,
    ClipboardReadRequest,
    ClipboardResult,
    ClipboardWriteRequest,
    CoordinateSpace,
    DisplayInfo,
    InputModifier,
    KeyboardHotkeyRequest,
    KeyboardKeyRequest,
    KeyboardTypeRequest,
    MonitorInfo,
    MouseButton,
    MouseClickRequest,
    MouseMoveRequest,
    MouseScrollRequest,
    OSActionRequest,
    OSActionResult,
    OSVerificationResult,
    Point2D,
    Rect2D,
    ScreenCaptureRequest,
    ScreenCaptureResult,
    ScreenInfo,
    SystemInfo,
    SystemInfoResult,
    VerificationMethod,
    VerificationRequest,
    WindowAction,
    WindowActionRequest,
    WindowInfo,
    WindowQuery,
    WindowState,
)


def test_geometry_primitives():
    pt = Point2D(x=100, y=200)
    assert pt.x == 100
    assert pt.y == 200

    rect = Rect2D(x=10, y=20, width=800, height=600)
    assert rect.x == 10
    assert rect.y == 20
    assert rect.width == 800
    assert rect.height == 600


def test_enums_and_constants():
    assert CoordinateSpace.SCREEN == "SCREEN"
    assert CoordinateSpace.MONITOR == "MONITOR"
    assert CoordinateSpace.WINDOW == "WINDOW"

    assert MouseButton.LEFT == "LEFT"
    assert MouseButton.RIGHT == "RIGHT"
    assert MouseButton.MIDDLE == "MIDDLE"

    assert WindowAction.FOCUS == "FOCUS"
    assert WindowAction.MINIMIZE == "MINIMIZE"
    assert WindowAction.MAXIMIZE == "MAXIMIZE"
    assert WindowAction.RESTORE == "RESTORE"

    assert WindowState.NORMAL == "normal"
    assert WindowState.MINIMIZED == "minimized"
    assert WindowState.MAXIMIZED == "maximized"

    assert InputModifier.CTRL == "ctrl"
    assert InputModifier.ALT == "alt"


def test_monitor_and_screen_info():
    mon = MonitorInfo(
        id=0,
        name="Primary Display",
        x=0,
        y=0,
        width=1920,
        height=1080,
        is_primary=True,
        scaling=1.25,
    )
    assert mon.is_primary is True
    assert mon.scaling == 1.25

    screen = ScreenInfo(
        virtual_x=0,
        virtual_y=0,
        virtual_width=1920,
        virtual_height=1080,
        monitors=[mon],
        primary_monitor_id=0,
    )
    assert screen.virtual_width == 1920
    assert len(screen.monitors) == 1
    assert DisplayInfo == ScreenInfo


def test_screen_capture_models():
    req = ScreenCaptureRequest(
        monitor_id=0,
        region=(10, 10, 200, 150),
        image_format="jpeg",
        max_width=100,
    )
    assert req.region == (10, 10, 200, 150)
    assert req.image_format == "jpeg"

    res = ScreenCaptureResult(
        image_path="screens/shot1.png",
        width=1920,
        height=1080,
        format="png",
        size_bytes=1048576,
    )
    assert res.file_path == "screens/shot1.png"
    assert res.image_path == "screens/shot1.png"


def test_mouse_requests():
    move = MouseMoveRequest(x=500, y=300, coordinate_space=CoordinateSpace.SCREEN)
    assert move.x == 500
    assert move.coordinate_space == CoordinateSpace.SCREEN

    click = MouseClickRequest(button=MouseButton.RIGHT, clicks=2)
    assert click.button == MouseButton.RIGHT
    assert click.clicks == 2

    scroll = MouseScrollRequest(delta=3, direction="down")
    assert scroll.clicks == 3
    assert scroll.direction == "down"


def test_keyboard_requests():
    type_req = KeyboardTypeRequest(text="Hello, JARVIS!", delay_ms=10)
    assert type_req.text == "Hello, JARVIS!"
    assert type_req.delay_ms == 10

    key_req = KeyboardKeyRequest(key="ENTER")
    assert key_req.key == "ENTER"

    hotkey_req = KeyboardHotkeyRequest(keys=["CTRL", "C"])
    assert hotkey_req.keys == ["CTRL", "C"]


def test_window_models():
    win = WindowInfo(
        handle_id=12345,
        title="Notepad",
        process_id=999,
        process_name="notepad.exe",
        x=100,
        y=100,
        width=800,
        height=600,
        is_foreground=True,
    )
    assert win.title == "Notepad"
    assert win.bounds.width == 800
    assert win.is_active is True

    query = WindowQuery(title="Notepad", exact_match=False)
    assert query.title == "Notepad"

    act_req = WindowActionRequest(handle_id=12345, action=WindowAction.MAXIMIZE)
    assert act_req.action == WindowAction.MAXIMIZE


def test_clipboard_models():
    read_req = ClipboardReadRequest(max_chars=1000)
    assert read_req.max_chars == 1000

    write_req = ClipboardWriteRequest(text="Copied text")
    assert write_req.text == "Copied text"

    clear_req = ClipboardClearRequest()
    assert isinstance(clear_req, ClipboardClearRequest)

    res = ClipboardResult(text="Pasted text", length=11, success=True)
    assert res.length == 11

    data = ClipboardData(format=ClipboardFormat.TEXT, text="Sample", byte_length=6)
    assert data.format == ClipboardFormat.TEXT


def test_system_info_and_verification_models():
    sys_info = SystemInfo(
        os_name="Windows",
        os_version="11",
        architecture="x64",
        hostname="JarvisRig",
        cpu_count=8,
        memory_total_bytes=16000000000,
        memory_available_bytes=8000000000,
        foreground_window_title="Visual Studio Code",
    )
    assert sys_info.cpu_count == 8
    assert SystemInfoResult == SystemInfo

    v_req = VerificationRequest(
        method=VerificationMethod.WINDOW_TITLE,
        expected_value="Untitled - Notepad",
    )
    assert v_req.method == VerificationMethod.WINDOW_TITLE

    v_res = OSVerificationResult(
        verified=True,
        observation="Window title matched expected value",
        confidence=1.0,
    )
    assert v_res.verified is True


def test_envelope_models():
    req = OSActionRequest(tool_id="os.mouse.click", parameters={"button": "LEFT"})
    assert req.tool_id == "os.mouse.click"
    assert req.action_id.startswith("act_")

    res = OSActionResult(
        action_id=req.action_id,
        tool_id=req.tool_id,
        success=True,
        output={"clicked": True},
        duration_ms=12.5,
    )
    assert res.success is True
    assert res.duration_ms == 12.5
