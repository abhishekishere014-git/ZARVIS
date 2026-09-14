"""Mouse pointer movement, click, and scroll tools registered with Phase 04."""

from typing import Any, Dict, Optional
from jarvis.os.models import CoordinateSpace, MouseButton, MouseClickRequest, MouseMoveRequest, MouseScrollRequest
from jarvis.os.tools.screen_tools import _get_manager
from jarvis.tools.decorator import tool
from jarvis.tools.models import ApprovalMode, RiskLevel, ToolExecutionContext, ToolPermission


@tool(
    name="mouse_move",
    tool_id="os.mouse.move",
    description="Positions the mouse pointer at specified coordinates within SCREEN, MONITOR, or WINDOW coordinate space.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def mouse_move(
    x: int,
    y: int,
    coordinate_space: str = "SCREEN",
    window_id: Optional[int] = None,
    monitor_id: Optional[int] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Moves mouse cursor.
    
    :param x: Target X coordinate
    :param y: Target Y coordinate
    :param coordinate_space: 'SCREEN', 'MONITOR', or 'WINDOW'
    :param window_id: Window HWND if coordinate_space is WINDOW
    :param monitor_id: Monitor ID if coordinate_space is MONITOR
    """
    mgr = _get_manager()
    space = CoordinateSpace(coordinate_space.upper())
    target_win = None
    if space == CoordinateSpace.WINDOW and window_id is not None:
        windows = mgr.window.list_windows()
        target_win = next((w for w in windows if w.handle_id == window_id), None)

    req = MouseMoveRequest(
        x=x,
        y=y,
        coordinate_space=space,
        window_id=window_id,
        monitor_id=monitor_id,
    )
    actual_x, actual_y = mgr.mouse.move(req, target_window=target_win)
    verification = mgr.verifier.verify_mouse_position(actual_x, actual_y)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "mouse_move", "x": actual_x, "y": actual_y, "verified": verification.verified},
    )

    return {
        "x": actual_x,
        "y": actual_y,
        "verified": verification.verified,
        "observation": verification.observation,
    }


@tool(
    name="mouse_click",
    tool_id="os.mouse.click",
    description="Clicks a mouse button at target coordinates or current cursor position.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "LEFT",
    clicks: int = 1,
    coordinate_space: str = "SCREEN",
    is_destructive: bool = False,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Sends mouse button clicks.
    
    :param x: Optional target X coordinate
    :param y: Optional target Y coordinate
    :param button: 'LEFT', 'RIGHT', or 'MIDDLE'
    :param clicks: Number of clicks (1 for single, 2 for double)
    :param coordinate_space: 'SCREEN', 'MONITOR', or 'WINDOW'
    :param is_destructive: True if this click is potentially consequential (triggers user approval)
    """
    mgr = _get_manager()
    space = CoordinateSpace(coordinate_space.upper())
    btn = MouseButton(button.upper())

    # Check approval in context
    is_approved = context.user_approved if context and hasattr(context, "user_approved") else True

    req = MouseClickRequest(
        x=x,
        y=y,
        button=btn,
        clicks=clicks,
        coordinate_space=space,
        is_destructive=is_destructive,
    )
    actual_x, actual_y = mgr.mouse.click(req, approved=is_approved)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "mouse_click", "button": btn.value, "clicks": clicks, "x": actual_x, "y": actual_y},
    )

    return {
        "clicked": True,
        "button": btn.value,
        "clicks": clicks,
        "position": (actual_x, actual_y),
    }


@tool(
    name="mouse_double_click",
    tool_id="os.mouse.double_click",
    description="Double-clicks left mouse button at target coordinates or current pointer position.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def mouse_double_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Double-clicks left mouse button."""
    return await mouse_click(x=x, y=y, button="LEFT", clicks=2, context=context)


@tool(
    name="mouse_right_click",
    tool_id="os.mouse.right_click",
    description="Right-clicks mouse button at target coordinates or current pointer position (e.g. context menu).",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def mouse_right_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Right-clicks mouse button."""
    return await mouse_click(x=x, y=y, button="RIGHT", clicks=1, context=context)


@tool(
    name="mouse_scroll",
    tool_id="os.mouse.scroll",
    description="Rotates mouse wheel vertically by specified number of clicks (positive=up, negative=down).",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def mouse_scroll(
    clicks: int,
    x: Optional[int] = None,
    y: Optional[int] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Scrolls mouse wheel.
    
    :param clicks: Scroll ticks (e.g. 3 for scroll up, -3 for scroll down)
    :param x: Optional pointer X position
    :param y: Optional pointer Y position
    """
    mgr = _get_manager()
    req = MouseScrollRequest(clicks=clicks, x=x, y=y)
    mgr.mouse.scroll(req)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "mouse_scroll", "clicks": clicks},
    )

    return {"scrolled": True, "clicks": clicks}
