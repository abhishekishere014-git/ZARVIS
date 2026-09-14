"""Read-only system information tool registered with Phase 04."""

from typing import Any, Dict, Optional
from jarvis.os.tools.screen_tools import _get_manager
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission


@tool(
    name="system_info",
    tool_id="os.system.info",
    description="Returns safe, read-only host telemetry including OS version, CPU count, RAM capacity, and active window.",
    category="os",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=5.0,
)
async def system_info(
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Retrieves safe system telemetry."""
    mgr = _get_manager()
    info = mgr.system.get_info()
    return info.model_dump()
