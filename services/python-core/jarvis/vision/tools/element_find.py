"""Element search and filtering tool registered with Phase 04 ToolRegistry."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission
from jarvis.vision.models import ElementType
from jarvis.vision.tools.screen_analyze import _get_manager


@tool(
    name="element_find",
    tool_id="vision.element.find",
    description="Finds visual UI elements on screen matching a semantic text query, element type, or region.",
    category="vision",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=10.0,
)
async def element_find(
    query: Optional[str] = None,
    element_type: Optional[str] = None,
    clickable_only: bool = False,
    monitor_id: int = 0,
    region_id: Optional[str] = None,
    force_refresh: bool = False,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Find visual elements on screen.

    :param query: Free-text search query (e.g. "submit button", "username input")
    :param element_type: Optional element type filter ('button', 'input_text', 'icon', etc.)
    :param clickable_only: If true, only return clickable elements
    :param monitor_id: Monitor index to search (default 0)
    :param region_id: Optional region ID to restrict search scope
    :param force_refresh: If true, take fresh screenshot before searching
    """
    mgr = _get_manager()

    parsed_type: Optional[ElementType] = None
    if element_type:
        try:
            parsed_type = ElementType(element_type.lower())
        except ValueError:
            pass

    elements = await mgr.find_elements(
        query=query,
        element_type=parsed_type,
        monitor_index=monitor_id,
        clickable_only=clickable_only,
        region_id=region_id,
        force_refresh=force_refresh,
    )

    # Sanitize elements for privacy
    sanitized = [mgr.security.sanitize_element(el) for el in elements]

    return {
        "success": True,
        "query": query,
        "match_count": len(sanitized),
        "elements": [el.to_summary() for el in sanitized],
    }
