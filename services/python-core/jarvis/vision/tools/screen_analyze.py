"""Screen visual analysis tool registered with Phase 04 ToolRegistry."""

from __future__ import annotations

from typing import Any, Dict, Optional
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission
from jarvis.vision.manager import VisionManager

_active_vision_manager: Optional[VisionManager] = None


def set_active_vision_manager(manager: VisionManager) -> None:
    global _active_vision_manager
    _active_vision_manager = manager


def _get_manager() -> VisionManager:
    global _active_vision_manager
    if not _active_vision_manager:
        _active_vision_manager = VisionManager()
    return _active_vision_manager


@tool(
    name="screen_analyze",
    tool_id="vision.screen.analyze",
    description="Analyzes the visual display screen, returning detected UI elements, text labels, and structural regions.",
    category="vision",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=15.0,
)
async def screen_analyze(
    monitor_id: int = 0,
    force_refresh: bool = False,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Analyze current screen visually.

    :param monitor_id: Monitor index to analyze (default 0)
    :param force_refresh: If true, ignore cache and take a fresh screenshot
    """
    mgr = _get_manager()
    obs = await mgr.capture_and_analyze(
        monitor_index=monitor_id,
        force_refresh=force_refresh,
    )

    # Sanitize observation before returning across tool boundary
    sanitized = mgr.security.sanitize_observation(obs)

    return {
        "success": True,
        "observation_id": sanitized.observation_id,
        "timestamp": sanitized.timestamp,
        "age_seconds": round(sanitized.age(), 2),
        "dimensions": {"width": sanitized.image_width, "height": sanitized.image_height},
        "active_window": sanitized.active_window_title,
        "element_count": len(sanitized.elements),
        "region_count": len(sanitized.regions),
        "elements": [el.to_summary() for el in sanitized.elements],
        "regions": [reg.to_summary() for reg in sanitized.regions],
    }
