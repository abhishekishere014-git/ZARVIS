"""Deterministic Mock OS provider for testing and headless environments."""

import io
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw
from jarvis.os.models import (
    MonitorInfo,
    MouseButton,
    ScreenInfo,
    SystemInfo,
    WindowAction,
    WindowInfo,
)
from jarvis.os.providers.base import OSProvider


class MockOSProvider(OSProvider):
    """Predictable virtual Windows desktop provider."""

    def __init__(
        self,
        screen_width: int = 1920,
        screen_height: int = 1080,
        virtual_width: Optional[int] = None,
        virtual_height: Optional[int] = None,
        **kwargs,
    ) -> None:
        self.screen_width = virtual_width or screen_width
        self.screen_height = virtual_height or screen_height
        self.cursor_x = 100
        self.cursor_y = 100
        self.click_history: List[Tuple[MouseButton, int, int, int]] = []
        self.scroll_history: List[int] = []
        self.typed_text: List[str] = []
        self.pressed_keys: List[str] = []
        self.hotkeys: List[List[str]] = []
        self.clipboard_content: str = ""

        # Setup virtual windows
        self.windows: Dict[int, WindowInfo] = {
            1001: WindowInfo(
                handle_id=1001,
                title="Calculator",
                process_name="calculator.exe",
                process_id=4520,
                x=200,
                y=150,
                width=400,
                height=500,
                is_foreground=False,
            ),
            1002: WindowInfo(
                handle_id=1002,
                title="Notepad - Untitled",
                process_name="notepad.exe",
                process_id=5812,
                x=650,
                y=150,
                width=800,
                height=600,
                is_foreground=True,
            ),
        }
        self.foreground_handle: int = 1002

    def is_available(self) -> bool:
        return True

    def get_screen_info(self) -> ScreenInfo:
        return ScreenInfo(
            virtual_x=0,
            virtual_y=0,
            virtual_width=self.screen_width,
            virtual_height=self.screen_height,
            monitors=[
                MonitorInfo(
                    id=0,
                    name="Mock Display 1",
                    x=0,
                    y=0,
                    width=self.screen_width,
                    height=self.screen_height,
                    is_primary=True,
                )
            ],
            primary_monitor_id=0,
        )

    def capture_screen(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        monitor_id: Optional[int] = None,
        image_format: str = "png",
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> bytes:
        w = self.screen_width
        h = self.screen_height
        if region:
            _, _, w, h = region

        # Generate a lightweight virtual desktop canvas
        img = Image.new("RGB", (w, h), color=(30, 30, 35))
        draw = ImageDraw.Draw(img)
        # Draw simulated window boxes
        if w > 120 and h > 120:
            draw.rectangle([50, 50, w - 50, h - 50], outline=(70, 70, 80), width=2)
            draw.text((60, 60), "JARVIS Mock Desktop Canvas", fill=(200, 200, 200))

        if max_width or max_height:
            target_w = min(w, max_width or w)
            target_h = min(h, max_height or h)
            img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)

        out_io = io.BytesIO()
        fmt = "JPEG" if image_format.lower() in ("jpeg", "jpg") else "PNG"
        img.save(out_io, format=fmt)
        return out_io.getvalue()

    def get_cursor_pos(self) -> Tuple[int, int]:
        return self.cursor_x, self.cursor_y

    def move_cursor(self, x: int, y: int) -> None:
        self.cursor_x = x
        self.cursor_y = y

    def mouse_click(self, button: MouseButton = MouseButton.LEFT, clicks: int = 1) -> None:
        self.click_history.append((button, clicks, self.cursor_x, self.cursor_y))

    def mouse_scroll(self, clicks: int) -> None:
        self.scroll_history.append(clicks)

    def type_text(self, text: str, delay_ms: float = 10.0) -> None:
        self.typed_text.append(text)

    def press_key(self, key: str, duration_sec: float = 0.05) -> None:
        self.pressed_keys.append(key)

    def send_hotkey(self, keys: List[str]) -> None:
        self.hotkeys.append(keys)

    def list_windows(self) -> List[WindowInfo]:
        return list(self.windows.values())

    def get_foreground_window(self) -> Optional[WindowInfo]:
        return self.windows.get(self.foreground_handle)

    def set_foreground_window(self, handle_id: int) -> bool:
        if handle_id in self.windows:
            if self.foreground_handle in self.windows:
                self.windows[self.foreground_handle].is_foreground = False
            self.foreground_handle = handle_id
            self.windows[handle_id].is_foreground = True
            return True
        return False

    def set_window_state(self, handle_id: int, action: WindowAction) -> bool:
        if handle_id not in self.windows:
            return False
        win = self.windows[handle_id]
        if action == WindowAction.MINIMIZE:
            win.is_minimized = True
            win.is_maximized = False
        elif action == WindowAction.MAXIMIZE:
            win.is_maximized = True
            win.is_minimized = False
        elif action == WindowAction.RESTORE:
            win.is_minimized = False
            win.is_maximized = False
        elif action == WindowAction.FOCUS:
            self.set_foreground_window(handle_id)
        return True

    def read_clipboard(self) -> str:
        return self.clipboard_content

    def write_clipboard(self, text: str) -> bool:
        self.clipboard_content = text
        return True

    def clear_clipboard(self) -> bool:
        self.clipboard_content = ""
        return True

    def get_system_info(self) -> SystemInfo:
        fg_title = self.windows[self.foreground_handle].title if self.foreground_handle in self.windows else None
        return SystemInfo(
            os_name="Windows (Mock)",
            os_version="10.0.22631",
            architecture="AMD64",
            hostname="JARVIS-VIRTUAL-NODE",
            cpu_count=8,
            memory_total_bytes=16 * 1024 * 1024 * 1024,
            memory_available_bytes=8 * 1024 * 1024 * 1024,
            foreground_window_title=fg_title,
        )
