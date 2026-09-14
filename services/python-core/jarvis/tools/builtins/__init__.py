"""Built-in tool packages for JARVIS."""

from jarvis.tools.builtins.office import register_office_tools
from jarvis.tools.registry import ToolRegistry


def register_os_tools(registry: ToolRegistry, os_manager=None) -> None:
    """Registers Phase 08 OS Automation tools with ToolRegistry."""
    from jarvis.os.tools.registration import register_os_tools as _register_os
    _register_os(registry, os_manager=os_manager)


def register_vision_tools(registry: ToolRegistry, vision_manager=None) -> None:
    """Registers Phase 09 Vision tools with ToolRegistry."""
    from jarvis.vision.tools.registration import register_vision_tools as _register_vis
    _register_vis(registry, vision_manager=vision_manager)


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Registers all built-in tool suites into the given ToolRegistry."""
    register_office_tools(registry)


__all__ = ["register_builtin_tools", "register_office_tools", "register_os_tools", "register_vision_tools"]
