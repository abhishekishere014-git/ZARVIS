"""OS Automation tool package exposing tools and registration."""

from jarvis.os.tools.clipboard_tools import (
    clipboard_clear,
    clipboard_read,
    clipboard_write,
)
from jarvis.os.tools.keyboard_tools import (
    keyboard_hotkey,
    keyboard_press,
    keyboard_type,
)
from jarvis.os.tools.mouse_tools import (
    mouse_click,
    mouse_double_click,
    mouse_move,
    mouse_right_click,
    mouse_scroll,
)
from jarvis.os.tools.registration import (
    ALL_OS_TOOLS,
    register_os_tools,
    set_active_os_manager,
)
from jarvis.os.tools.screen_tools import (
    screen_capture,
    screen_info,
    screen_monitors,
)
from jarvis.os.tools.system_tools import system_info
from jarvis.os.tools.window_tools import (
    window_focus,
    window_list,
    window_maximize,
    window_minimize,
    window_restore,
)

__all__ = [
    "ALL_OS_TOOLS",
    "clipboard_clear",
    "clipboard_read",
    "clipboard_write",
    "keyboard_hotkey",
    "keyboard_press",
    "keyboard_type",
    "mouse_click",
    "mouse_double_click",
    "mouse_move",
    "mouse_right_click",
    "mouse_scroll",
    "register_os_tools",
    "screen_capture",
    "screen_info",
    "screen_monitors",
    "set_active_os_manager",
    "system_info",
    "window_focus",
    "window_list",
    "window_maximize",
    "window_minimize",
    "window_restore",
]
