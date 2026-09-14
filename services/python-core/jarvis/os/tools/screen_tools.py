"""Screen capture and monitor inspection tools registered with Phase 04."""

from typing import Any, Dict, List, Optional, Tuple
from jarvis.os.manager import OSAutomationManager
from jarvis.os.models import ScreenCaptureRequest
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission

# Global instance injected by register_os_tools
_active_os_manager: Optional[OSAutomationManager] = None


def set_active_os_manager(manager: OSAutomationManager) -> None:
    global _active_os_manager
    _active_os_manager = manager


def _get_manager() -> OSAutomationManager:
    if not _active_os_manager:
        raise ValueError("OSAutomationManager has not been initialized.")
    return _active_os_manager


@tool(
    name="screen_capture",
    tool_id="os.screen.capture",
    description="Captures visual display pixels of a monitor or region and saves to the sandboxed temp directory.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=10.0,
)
async def screen_capture(
    monitor_id: Optional[int] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    image_format: str = "png",
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Captures desktop screen imagery.
    
    :param monitor_id: Optional monitor index to capture
    :param x: Optional bounding region left
    :param y: Optional bounding region top
    :param width: Optional bounding region width
    :param height: Optional bounding region height
    :param image_format: Output image format ('png' or 'jpeg')
    :param max_width: Downscale width ceiling
    :param max_height: Downscale height ceiling
    """
    mgr = _get_manager()
    region = (x, y, width, height) if None not in (x, y, width, height) else None

    req = ScreenCaptureRequest(
        monitor_id=monitor_id,
        region=region,
        image_format=image_format,
        max_width=max_width,
        max_height=max_height,
        include_base64=False,
    )
    result = mgr.screen.capture(req)
    corr_id = context.correlation_id if context else "default_corr"
    await mgr.emit_event(
        "os.screen.captured",
        corr_id,
        {"width": result.width, "height": result.height, "size_bytes": result.size_bytes},
    )

    return result.model_dump(exclude={"image_base64"})


@tool(
    name="screen_monitors",
    tool_id="os.screen.monitors",
    description="Lists all connected display monitors and their pixel coordinates and resolutions.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def screen_monitors(
    context: Optional[ToolExecutionContext] = None,
) -> List[Dict[str, Any]]:
    """Returns list of connected display monitors and resolutions."""
    mgr = _get_manager()
    monitors = mgr.monitor.list_monitors()
    return [m.model_dump() for m in monitors]


@tool(
    name="screen_info",
    tool_id="os.screen.info",
    description="Returns full virtual desktop geometry across all active monitors.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def screen_info(
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Returns overall desktop geometry across all screens."""
    mgr = _get_manager()
    return mgr.monitor.get_screen_info().model_dump()
