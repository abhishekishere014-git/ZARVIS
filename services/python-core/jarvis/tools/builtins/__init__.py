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


def register_browser_tools(registry: ToolRegistry) -> None:
    """Registers Browser and YouTube automation tools with ToolRegistry."""
    from jarvis.tools.builtins.browser_tools import (
        browser_open,
        browser_search,
        youtube_search_and_play,
    )
    for tool_fn in [browser_open, browser_search, youtube_search_and_play]:
        tool_def = getattr(tool_fn, "tool_definition", None)
        if tool_def and registry.has(tool_def.id):
            continue
        registry.register_tool(tool_fn)


def register_app_tools(registry: ToolRegistry) -> None:
    """Registers desktop application launch, focus, and close tools."""
    from jarvis.os.tools.app_tools import app_launch, app_focus, app_close
    for tool_fn in [app_launch, app_focus, app_close]:
        tool_def = getattr(tool_fn, "tool_definition", None)
        if tool_def and registry.has(tool_def.id):
            continue
        registry.register_tool(tool_fn)


def register_file_tools(registry: ToolRegistry) -> None:
    """Registers user directory and workspace file management tools."""
    from jarvis.os.tools.file_tools import file_open_directory, file_list_files, file_create_text_file
    for tool_fn in [file_open_directory, file_list_files, file_create_text_file]:
        tool_def = getattr(tool_fn, "tool_definition", None)
        if tool_def and registry.has(tool_def.id):
            continue
        registry.register_tool(tool_fn)


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Registers all built-in tool suites into the given ToolRegistry."""
    register_office_tools(registry)
    register_browser_tools(registry)
    register_app_tools(registry)
    register_file_tools(registry)


__all__ = [
    "register_builtin_tools",
    "register_office_tools",
    "register_os_tools",
    "register_vision_tools",
    "register_browser_tools",
    "register_app_tools",
    "register_file_tools",
]
