"""Abstract base protocol for OS automation providers."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from jarvis.os.models import (
    CoordinateSpace,
    MouseButton,
    ScreenInfo,
    SystemInfo,
    WindowAction,
    WindowInfo,
)


class OSProvider(ABC):
    """Abstract interface defining required OS automation capabilities."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if this provider can execute on the host platform."""
        pass

    # Screen
    @abstractmethod
    def get_screen_info(self) -> ScreenInfo:
        """Returns geometry and metadata of all displays."""
        pass

    @abstractmethod
    def capture_screen(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        monitor_id: Optional[int] = None,
        image_format: str = "png",
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> bytes:
        """Captures screen pixels and returns image file bytes (PNG or JPEG)."""
        pass

    # Mouse
    @abstractmethod
    def get_cursor_pos(self) -> Tuple[int, int]:
        """Returns current virtual desktop coordinates (x, y) of the mouse pointer."""
        pass

    @abstractmethod
    def move_cursor(self, x: int, y: int) -> None:
        """Moves cursor to virtual desktop coordinates (x, y)."""
        pass

    @abstractmethod
    def mouse_click(self, button: MouseButton = MouseButton.LEFT, clicks: int = 1) -> None:
        """Sends mouse click events at the current pointer position."""
        pass

    @abstractmethod
    def mouse_scroll(self, clicks: int) -> None:
        """Sends vertical mouse wheel scroll events."""
        pass

    # Keyboard
    @abstractmethod
    def type_text(self, text: str, delay_ms: float = 10.0) -> None:
        """Types unicode string using virtual keystrokes."""
        pass

    @abstractmethod
    def press_key(self, key: str, duration_sec: float = 0.05) -> None:
        """Presses and releases a single key."""
        pass

    @abstractmethod
    def send_hotkey(self, keys: List[str]) -> None:
        """Presses keys down in sequence, then releases in reverse order."""
        pass

    # Window
    @abstractmethod
    def list_windows(self) -> List[WindowInfo]:
        """Enumerates visible application windows."""
        pass

    @abstractmethod
    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Returns metadata of currently focused window."""
        pass

    @abstractmethod
    def set_foreground_window(self, handle_id: int) -> bool:
        """Brings the specified window into the foreground."""
        pass

    @abstractmethod
    def set_window_state(self, handle_id: int, action: WindowAction) -> bool:
        """Alters window state (MINIMIZE, MAXIMIZE, RESTORE)."""
        pass

    # Clipboard
    @abstractmethod
    def read_clipboard(self) -> str:
        """Reads plain text from system clipboard."""
        pass

    @abstractmethod
    def write_clipboard(self, text: str) -> bool:
        """Writes plain text to system clipboard."""
        pass

    @abstractmethod
    def clear_clipboard(self) -> bool:
        """Clears system clipboard contents."""
        pass

    # System
    @abstractmethod
    def get_system_info(self) -> SystemInfo:
        """Returns safe, read-only system telemetry."""
        pass
