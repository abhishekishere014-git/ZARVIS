"""Built-in tool packages for JARVIS."""

from jarvis.tools.builtins.office import register_office_tools
from jarvis.tools.registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Registers all built-in tool suites into the given ToolRegistry."""
    register_office_tools(registry)


__all__ = ["register_builtin_tools", "register_office_tools"]
