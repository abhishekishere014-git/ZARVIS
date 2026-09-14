"""Registration logic for Phase 09 Vision tools with Phase 04 ToolRegistry."""

from typing import List, Optional
from jarvis.tools.registry import ToolRegistry
from jarvis.vision.manager import VisionManager
from jarvis.vision.tools.element_find import element_find
from jarvis.vision.tools.screen_analyze import screen_analyze, set_active_vision_manager
from jarvis.vision.tools.target_resolve import target_resolve

ALL_VISION_TOOLS = [
    screen_analyze,
    element_find,
    target_resolve,
]


def register_vision_tools(
    registry: ToolRegistry, vision_manager: Optional[VisionManager] = None
) -> List[str]:
    """Registers all Vision tools with the given ToolRegistry.

    :param registry: ToolRegistry instance
    :param vision_manager: Optional VisionManager instance to associate with tools
    :return: List of registered tool IDs
    """
    if vision_manager is not None:
        set_active_vision_manager(vision_manager)

    registered_ids = []
    for tool_fn in ALL_VISION_TOOLS:
        registry.register_tool(tool_fn)
        tool_def = getattr(tool_fn, "tool_definition", None)
        tool_id = tool_def.id if tool_def else getattr(tool_fn, "tool_id", getattr(tool_fn, "__name__", "unknown"))
        registered_ids.append(tool_id)

    return registered_ids


__all__ = [
    "ALL_VISION_TOOLS",
    "register_vision_tools",
    "set_active_vision_manager",
]
