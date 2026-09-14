"""Windows-specific OS automation provider using native Win32 APIs and Pillow."""

import ctypes
from ctypes import wintypes
import io
import logging
import os
import platform
import sys
import time
from typing import Dict, List, Optional, Tuple
from PIL import Image
from jarvis.os.errors import (
    ClipboardError,
    MouseActionError,
    ScreenCaptureError,
    WindowManagementError,
)
from jarvis.os.models import (
    MonitorInfo,
    MouseButton,
    ScreenInfo,
    SystemInfo,
    WindowAction,
    WindowInfo,
)
from jarvis.os.providers.base import OSProvider

logger = logging.getLogger("jarvis.os.providers.windows")

# Win32 Constants
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9

CF_UNICODETEXT = 13

# VK Code mappings
VK_MAP: Dict[str, int] = {
    "CTRL": 0x11, "CONTROL": 0x11,
    "ALT": 0x12,
    "SHIFT": 0x10,
    "WIN": 0x5B, "WINDOWS": 0x5B,
    "ENTER": 0x0D, "RETURN": 0x0D,
    "ESC": 0x1B, "ESCAPE": 0x1B,
    "TAB": 0x09,
    "SPACE": 0x20,
    "BACKSPACE": 0x08,
    "DELETE": 0x2E, "DEL": 0x2E,
    "INSERT": 0x2D,
    "HOME": 0x24, "END": 0x23,
    "PAGEUP": 0x21, "PGUP": 0x21,
    "PAGEDOWN": 0x22, "PGDN": 0x22,
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    "CAPSLOCK": 0x14,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75,
    "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class WindowsOSProvider(OSProvider):
    """Production Windows OS automation provider backed by User32, Gdi32, and Kernel32."""

    def __init__(self) -> None:
        self._user32 = None
        self._gdi32 = None
        self._kernel32 = None
        if sys.platform == "win32":
            try:
                self._user32 = ctypes.windll.user32
                self._gdi32 = ctypes.windll.gdi32
                self._kernel32 = ctypes.windll.kernel32
            except Exception as exc:
                logger.warning("Failed to load Windows DLLs: %s", exc)

    def is_available(self) -> bool:
        return (
            sys.platform == "win32"
            and self._user32 is not None
            and self._gdi32 is not None
        )

    # 1. Screen
    def get_screen_info(self) -> ScreenInfo:
        if not self.is_available():
            return ScreenInfo(virtual_width=1920, virtual_height=1080)

        vx = self._user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        vy = self._user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        vw = self._user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        vh = self._user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

        if vw == 0 or vh == 0:
            # Fallback to primary screen
            vw = self._user32.GetSystemMetrics(0)
            vh = self._user32.GetSystemMetrics(1)
            vx = 0
            vy = 0

        monitors = [
            MonitorInfo(
                id=0,
                name="Primary Monitor",
                x=vx,
                y=vy,
                width=vw,
                height=vh,
                is_primary=True,
            )
        ]

        return ScreenInfo(
            virtual_x=vx,
            virtual_y=vy,
            virtual_width=vw,
            virtual_height=vh,
            monitors=monitors,
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
        if not self.is_available():
            raise ScreenCaptureError("Windows screen capture is unavailable on this platform.")

        info = self.get_screen_info()
        x, y, w, h = info.virtual_x, info.virtual_y, info.virtual_width, info.virtual_height

        if region:
            x, y, w, h = region

        # Win32 GDI screen capture
        hwin = self._user32.GetDesktopWindow()
        hwindc = self._user32.GetWindowDC(hwin)
        srcdc = self._gdi32.CreateCompatibleDC(hwindc)
        bmp = self._gdi32.CreateCompatibleBitmap(hwindc, w, h)
        self._gdi32.SelectObject(srcdc, bmp)

        try:
            # SRCCOPY = 0x00CC0020
            self._gdi32.BitBlt(srcdc, 0, 0, w, h, hwindc, x, y, 0x00CC0020)

            # Extract bitmap bits
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wintypes.DWORD),
                    ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long),
                    ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD),
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h  # top-down DIB
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            buf_size = w * h * 4
            buffer = ctypes.create_string_buffer(buf_size)
            self._gdi32.GetDIBits(srcdc, bmp, 0, h, buffer, ctypes.byref(bmi), 0)

            # Create PIL image from BGRA buffer
            img = Image.frombuffer("RGBA", (w, h), buffer, "raw", "BGRA", 0, 1)
            img = img.convert("RGB")

            # Handle downscaling if requested
            if max_width or max_height:
                target_w = min(w, max_width or w)
                target_h = min(h, max_height or h)
                img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)

            out_io = io.BytesIO()
            fmt = "JPEG" if image_format.lower() in ("jpeg", "jpg") else "PNG"
            img.save(out_io, format=fmt)
            return out_io.getvalue()

        except Exception as exc:
            raise ScreenCaptureError(f"GDI Screen capture failed: {exc}")
        finally:
            self._gdi32.DeleteObject(bmp)
            self._gdi32.DeleteDC(srcdc)
            self._user32.ReleaseDC(hwin, hwindc)

    # 2. Mouse
    def get_cursor_pos(self) -> Tuple[int, int]:
        if not self.is_available():
            return 0, 0
        pt = POINT()
        self._user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def move_cursor(self, x: int, y: int) -> None:
        if not self.is_available():
            return
        if not self._user32.SetCursorPos(x, y):
            raise MouseActionError(f"Failed to set cursor position to ({x}, {y})")

    def mouse_click(self, button: MouseButton = MouseButton.LEFT, clicks: int = 1) -> None:
        if not self.is_available():
            return

        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        if button == MouseButton.RIGHT:
            down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif button == MouseButton.MIDDLE:
            down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP

        for _ in range(clicks):
            self._user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.01)
            self._user32.mouse_event(up_flag, 0, 0, 0, 0)
            if clicks > 1:
                time.sleep(0.05)

    def mouse_scroll(self, clicks: int) -> None:
        if not self.is_available():
            return
        # WHEEL_DELTA = 120 per click
        wheel_amount = clicks * 120
        self._user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)

    # 3. Keyboard
    def type_text(self, text: str, delay_ms: float = 10.0) -> None:
        if not self.is_available():
            return
        delay_sec = delay_ms / 1000.0

        for char in text:
            code = ord(char)
            # Send unicode character event
            self._user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
            self._user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
            if delay_sec > 0:
                time.sleep(delay_sec)

    def _resolve_vk_code(self, key: str) -> int:
        normalized = key.strip().upper()
        if normalized in VK_MAP:
            return VK_MAP[normalized]
        if len(key) == 1:
            # Alpha / digit
            return self._user32.VkKeyScanW(ord(key)) & 0xFF
        raise KeyboardActionError(f"Cannot resolve key '{key}' to virtual key code")

    def press_key(self, key: str, duration_sec: float = 0.05) -> None:
        if not self.is_available():
            return
        vk = self._resolve_vk_code(key)
        self._user32.keybd_event(vk, 0, 0, 0)
        time.sleep(duration_sec)
        self._user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    def send_hotkey(self, keys: List[str]) -> None:
        if not self.is_available():
            return
        vk_codes = [self._resolve_vk_code(k) for k in keys]
        # Press all keys in sequence
        for vk in vk_codes:
            self._user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.01)
        # Release in reverse order
        for vk in reversed(vk_codes):
            self._user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)

    # 4. Window
    def list_windows(self) -> List[WindowInfo]:
        if not self.is_available():
            return []

        windows: List[WindowInfo] = []
        fg_hwnd = self._user32.GetForegroundWindow()

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def enum_cb(hwnd, lparam):
            if not self._user32.IsWindowVisible(hwnd):
                return True
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True

            title_buf = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, title_buf, length + 1)
            title = title_buf.value.strip()
            if not title:
                return True

            rect = RECT()
            self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top

            # Skip tiny invisible helper windows
            if w <= 1 or h <= 1:
                return True

            pid = wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            windows.append(
                WindowInfo(
                    handle_id=int(hwnd),
                    title=title,
                    process_id=int(pid.value),
                    x=rect.left,
                    y=rect.top,
                    width=w,
                    height=h,
                    is_foreground=(hwnd == fg_hwnd),
                    is_visible=True,
                )
            )
            return True

        self._user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return windows

    def get_foreground_window(self) -> Optional[WindowInfo]:
        if not self.is_available():
            return None
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None

        length = self._user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            title_buf = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, title_buf, length + 1)
            title = title_buf.value

        rect = RECT()
        self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
        pid = wintypes.DWORD()
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        return WindowInfo(
            handle_id=int(hwnd),
            title=title,
            process_id=int(pid.value),
            x=rect.left,
            y=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            is_foreground=True,
        )

    def set_foreground_window(self, handle_id: int) -> bool:
        if not self.is_available():
            return False
        # If minimized, restore first
        self._user32.ShowWindow(handle_id, SW_RESTORE)
        res = self._user32.SetForegroundWindow(handle_id)
        return bool(res)

    def set_window_state(self, handle_id: int, action: WindowAction) -> bool:
        if not self.is_available():
            return False
        cmd = SW_RESTORE
        if action == WindowAction.MINIMIZE:
            cmd = SW_MINIMIZE
        elif action == WindowAction.MAXIMIZE:
            cmd = SW_MAXIMIZE
        elif action == WindowAction.RESTORE or action == WindowAction.FOCUS:
            cmd = SW_RESTORE

        res = self._user32.ShowWindow(handle_id, cmd)
        if action == WindowAction.FOCUS:
            self._user32.SetForegroundWindow(handle_id)
        return True

    # 5. Clipboard
    def read_clipboard(self) -> str:
        if not self.is_available():
            return ""

        if not self._user32.OpenClipboard(None):
            raise ClipboardError("Failed to open Windows clipboard for reading")

        try:
            handle = self._user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""

            ptr = self._kernel32.GlobalLock(handle)
            if not ptr:
                return ""

            try:
                text = ctypes.c_wchar_p(ptr).value or ""
                return text
            finally:
                self._kernel32.GlobalUnlock(handle)
        finally:
            self._user32.CloseClipboard()

    def write_clipboard(self, text: str) -> bool:
        if not self.is_available():
            return False

        if not self._user32.OpenClipboard(None):
            raise ClipboardError("Failed to open Windows clipboard for writing")

        try:
            self._user32.EmptyClipboard()
            # GMEM_MOVEABLE = 0x0002
            size = (len(text) + 1) * ctypes.sizeof(ctypes.c_wchar)
            h_mem = self._kernel32.GlobalAlloc(0x0002, size)
            if not h_mem:
                raise ClipboardError("Failed to allocate memory for clipboard")

            ptr = self._kernel32.GlobalLock(h_mem)
            if not ptr:
                raise ClipboardError("Failed to lock global memory")

            try:
                ctypes.memmove(ptr, ctypes.c_wchar_p(text), size)
            finally:
                self._kernel32.GlobalUnlock(h_mem)

            if not self._user32.SetClipboardData(CF_UNICODETEXT, h_mem):
                self._kernel32.GlobalFree(h_mem)
                raise ClipboardError("Failed to set clipboard data")
            return True
        finally:
            self._user32.CloseClipboard()

    def clear_clipboard(self) -> bool:
        if not self.is_available():
            return False
        if not self._user32.OpenClipboard(None):
            raise ClipboardError("Failed to open clipboard to clear")
        try:
            return bool(self._user32.EmptyClipboard())
        finally:
            self._user32.CloseClipboard()

    # 6. System
    def get_system_info(self) -> SystemInfo:
        fg_title = None
        fg_win = self.get_foreground_window()
        if fg_win:
            fg_title = fg_win.title

        total_ram = 0
        avail_ram = 0
        if self.is_available() and self._kernel32:
            try:
                mem_status = MEMORYSTATUSEX()
                mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if self._kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status)):
                    total_ram = int(mem_status.ullTotalPhys)
                    avail_ram = int(mem_status.ullAvailPhys)
            except Exception:
                pass

        return SystemInfo(
            os_name="Windows",
            os_version=platform.version(),
            architecture=platform.machine(),
            hostname=platform.node(),
            cpu_count=os.cpu_count() or 1,
            memory_total_bytes=total_ram,
            memory_available_bytes=avail_ram,
            foreground_window_title=fg_title,
        )
