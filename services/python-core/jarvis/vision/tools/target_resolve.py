"""Semantic target resolution tool registered with Phase 04 ToolRegistry."""

from __future__ import annotations

from typing import Any, Dict, Optional
from jarvis.tools.decorator import tool
from jarvis.tools.models import RiskLevel, ToolExecutionContext, ToolPermission
from jarvis.vision.models import ElementType
from jarvis.vision.tools.screen_analyze import _get_manager


@tool(
    name="target_resolve",
    tool_id="vision.target.resolve",
    description="Resolves a semantic target description (e.g. 'Search button', 'username field') to validated pixel coordinates for OS automation.",
    category="vision",
    version="1.0.0",
    permissions={ToolPermission.READ},
    risk_level=RiskLevel.LOW,
    timeout_seconds=10.0,
)
async def target_resolve(
    query: str,
    monitor_id: int = 0,
    element_type: Optional[str] = None,
    clickable_only: bool = False,
    region_id: Optional[str] = None,
    min_confidence: Optional[float] = None,
    allow_ambiguous: bool = False,
    force_refresh: bool = False,
    context: Optional[ToolExecutionContext] = None,
) -> Dict[str, Any]:
    """Resolve a semantic query to screen coordinates.

    :param query: Natural language description of the target UI element
    :param monitor_id: Monitor index to search (default 0)
    :param element_type: Optional element type hint
    :param clickable_only: If true, only consider clickable elements
    :param region_id: Optional region ID to constrain search
    :param min_confidence: Minimum acceptable confidence score [0.0..1.0]
    :param allow_ambiguous: If true, returns best match even if score delta is small
    :param force_refresh: If true, capture fresh screenshot before resolving
    """
    mgr = _get_manager()

    parsed_type: Optional[ElementType] = None
    if element_type:
        try:
            parsed_type = ElementType(element_type.lower())
        except ValueError:
            pass

    result = await mgr.resolve_target(
        query=query,
        monitor_index=monitor_id,
        element_type=parsed_type,
        region_id=region_id,
        clickable_only=clickable_only,
        min_confidence=min_confidence,
        allow_ambiguous=allow_ambiguous,
        force_refresh=force_refresh,
    )

    return {
        "success": True,
        "query": result.query,
        "target_point": result.target_point.to_dict(),
        "element_id": result.element.element_id,
        "element_type": result.element.element_type.value,
        "confidence": round(result.confidence, 4),
        "confidence_level": result.confidence_level.value,
        "is_ambiguous": result.is_ambiguous,
        "bounds": result.element.bounds.to_dict(),
        "suggested_action": result.suggested_action,
        "candidate_count": len(result.candidates),
    }
