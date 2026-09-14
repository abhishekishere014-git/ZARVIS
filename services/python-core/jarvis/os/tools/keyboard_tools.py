"""Keyboard input, discrete key, and hotkey tools registered with Phase 04."""

from typing import Any, Dict, List, Optional
from jarvis.os.models import KeyboardHotkeyRequest, KeyboardKeyRequest, KeyboardTypeRequest
from jarvis.os.tools.screen_tools import _get_manager
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission


@tool(
    name="keyboard_type",
    tool_id="os.keyboard.type",
    description="Types unicode text string into the currently focused desktop window.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=10.0,
)
async def keyboard_type(
    text: str,
    delay_ms: float = 10.0,
    is_sensitive: bool = False,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Types text with virtual key events.
    
    :param text: Text string to type
    :param delay_ms: Delay in milliseconds between consecutive keystrokes
    :param is_sensitive: Flag indicating password/token typing requiring approval
    """
    mgr = _get_manager()
    is_approved = context.user_approved if context and hasattr(context, "user_approved") else True

    req = KeyboardTypeRequest(text=text, delay_ms=delay_ms, is_sensitive=is_sensitive)
    chars_typed = mgr.keyboard.type_text(req, approved=is_approved)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "keyboard_type", "chars_typed": chars_typed, "is_sensitive": is_sensitive},
    )

    return {"typed": True, "chars_count": chars_typed}


@tool(
    name="keyboard_press",
    tool_id="os.keyboard.press",
    description="Presses a single key from the supported allowlist (e.g. 'ENTER', 'ESC', 'TAB', 'SPACE').",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def keyboard_press(
    key: str,
    duration_sec: float = 0.05,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Presses and releases a single key.
    
    :param key: Key identifier from allowlist
    :param duration_sec: Press hold duration
    """
    mgr = _get_manager()
    req = KeyboardKeyRequest(key=key, duration_sec=duration_sec)
    valid_key = mgr.keyboard.press_key(req)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "keyboard_press", "key": valid_key},
    )

    return {"pressed": True, "key": valid_key}


@tool(
    name="keyboard_hotkey",
    tool_id="os.keyboard.hotkey",
    description="Executes a multi-key hotkey combination (e.g. ['CTRL', 'C'], ['ALT', 'TAB'], ['CTRL', 'SHIFT', 'ESC']).",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.EXECUTE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def keyboard_hotkey(
    keys: List[str],
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Sends a hotkey sequence.
    
    :param keys: List of keys in combo sequence
    """
    mgr = _get_manager()
    req = KeyboardHotkeyRequest(keys=keys)
    valid_keys = mgr.keyboard.send_hotkey(req)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "keyboard_hotkey", "keys": valid_keys},
    )

    return {"executed": True, "keys": valid_keys}
