"""Clipboard read, write, and clear tools registered with Phase 04."""

from typing import Any, Dict, Optional
from jarvis.os.models import ClipboardReadRequest, ClipboardWriteRequest
from jarvis.os.tools.screen_tools import _get_manager
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission


@tool(
    name="clipboard_read",
    tool_id="os.clipboard.read",
    description="Reads plain text currently stored in the system clipboard.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def clipboard_read(
    max_chars: Optional[int] = 50000,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Reads system clipboard text.
    
    :param max_chars: Maximum characters to retrieve
    """
    mgr = _get_manager()
    req = ClipboardReadRequest(max_chars=max_chars)
    res = mgr.clipboard.read(req)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "clipboard_read", "length": res.length},
    )

    return {"text": res.text, "length": res.length}


@tool(
    name="clipboard_write",
    tool_id="os.clipboard.write",
    description="Sets the text contents of the system clipboard.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.WRITE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def clipboard_write(
    text: str,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Sets system clipboard text.
    
    :param text: Text to place on clipboard
    """
    mgr = _get_manager()
    req = ClipboardWriteRequest(text=text)
    res = mgr.clipboard.write(req)
    verification = mgr.verifier.verify_clipboard_write(text)

    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.input.executed",
        corr_id,
        {"action": "clipboard_write", "length": res.length, "verified": verification.verified},
    )

    return {
        "success": res.success,
        "length": res.length,
        "verified": verification.verified,
    }


@tool(
    name="clipboard_clear",
    tool_id="os.clipboard.clear",
    description="Empties and clears the system clipboard.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.WRITE},
    risk_level=RiskLevel.MEDIUM,
    timeout_seconds=5.0,
)
async def clipboard_clear(
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Clears system clipboard."""
    mgr = _get_manager()
    success = mgr.clipboard.clear()
    return {"cleared": success}
