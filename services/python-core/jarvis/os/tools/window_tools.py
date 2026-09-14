"""Window discovery, targeting, and state management tools registered with Phase 04."""

from typing import Any, Dict, List, Optional
from jarvis.os.models import WindowAction, WindowQuery
from jarvis.os.tools.screen_tools import _get_manager
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission


@tool(
    name="window_list",
    tool_id="os.window.list",
    description="Enumerates all currently visible desktop windows, including titles, process IDs, and coordinates.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def window_list(
    context: Optional[ToolExecutionContext] = None,
) -> List[Dict[str, Any]]:
    """Lists visible desktop windows."""
    mgr = _get_manager()
    windows = mgr.window.list_windows()
    return [w.model_dump() for w in windows]


@tool(
    name="window_focus",
    tool_id="os.window.focus",
    description="Brings a target window into the foreground by handle ID or title search.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def window_focus(
    handle_id: Optional[int] = None,
    title_pattern: Optional[str] = None,
    process_name: Optional[str] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Focuses a desktop window.
    
    :param handle_id: Specific window handle/HWND
    :param title_pattern: Substring to match window title
    :param process_name: Substring to match process name
    """
    mgr = _get_manager()
    target_handle = handle_id

    if target_handle is None:
        query = WindowQuery(title_pattern=title_pattern, process_name=process_name)
        target_win = mgr.window.find_window(query)
        target_handle = target_win.handle_id

    success = mgr.window.set_foreground(target_handle)
    verification = mgr.verifier.verify_window_focus(target_handle)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.window.changed",
        corr_id,
        {"action": "focus", "handle_id": target_handle, "verified": verification.verified},
    )

    return {
        "focused": success,
        "handle_id": target_handle,
        "verified": verification.verified,
        "observation": verification.observation,
    }


@tool(
    name="window_minimize",
    tool_id="os.window.minimize",
    description="Minimizes the specified window to the taskbar.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def window_minimize(
    handle_id: int,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Minimizes window."""
    mgr = _get_manager()
    success = mgr.window.set_state(handle_id, WindowAction.MINIMIZE)
    return {"minimized": success, "handle_id": handle_id}


@tool(
    name="window_maximize",
    tool_id="os.window.maximize",
    description="Maximizes the specified window to fill the display.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def window_maximize(
    handle_id: int,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Maximizes window."""
    mgr = _get_manager()
    success = mgr.window.set_state(handle_id, WindowAction.MAXIMIZE)
    return {"maximized": success, "handle_id": handle_id}


@tool(
    name="window_restore",
    tool_id="os.window.restore",
    description="Restores a minimized or maximized window to its standard floating size.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def window_restore(
    handle_id: int,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Restores window."""
    mgr = _get_manager()
    success = mgr.window.set_state(handle_id, WindowAction.RESTORE)
    return {"restored": success, "handle_id": handle_id}
