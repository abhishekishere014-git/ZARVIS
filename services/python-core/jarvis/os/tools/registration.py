"""Registration logic for Phase 08 OS Automation tools with Phase 04 ToolRegistry."""

from typing import Optional
from jarvis.os.manager import OSAutomationManager
from jarvis.os.tools.screen_tools import (
    screen_capture,
    screen_monitors,
    screen_info,
    set_active_os_manager,
)
from jarvis.os.tools.mouse_tools import (
    mouse_move,
    mouse_click,
    mouse_double_click,
    mouse_right_click,
    mouse_scroll,
)
from jarvis.os.tools.keyboard_tools import (
    keyboard_type,
    keyboard_press,
    keyboard_hotkey,
)
from jarvis.os.tools.window_tools import (
    window_list,
    window_focus,
    window_minimize,
    window_maximize,
    window_restore,
)
from jarvis.os.tools.clipboard_tools import (
    clipboard_read,
    clipboard_write,
    clipboard_clear,
)
from jarvis.os.tools.system_tools import system_info
from jarvis.tools.registry import ToolRegistry


ALL_OS_TOOLS = [
    screen_capture,
    screen_monitors,
    screen_info,
    mouse_move,
    mouse_click,
    mouse_double_click,
    mouse_right_click,
    mouse_scroll,
    keyboard_type,
    keyboard_press,
    keyboard_hotkey,
    window_list,
    window_focus,
    window_minimize,
    window_maximize,
    window_restore,
    clipboard_read,
    clipboard_write,
    clipboard_clear,
    system_info,
]


def register_os_tools(registry: ToolRegistry, os_manager: Optional[OSAutomationManager] = None) -> None:
    """Registers all OS Automation tools with the given ToolRegistry.
    
    :param registry: ToolRegistry instance
    :param os_manager: Optional OSAutomationManager instance to associate with the tools
    """
    if os_manager is not None:
        set_active_os_manager(os_manager)

    for tool_fn in ALL_OS_TOOLS:
        registry.register_tool(tool_fn)


__all__ = [
    "ALL_OS_TOOLS",
    "register_os_tools",
    "set_active_os_manager",
]
