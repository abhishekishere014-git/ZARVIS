"""Domain models and contracts for JARVIS Controlled OS Automation."""

import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class Point2D(BaseModel):
    """Two-dimensional coordinate point."""
    x: int
    y: int


class Rect2D(BaseModel):
    """Two-dimensional rectangle region."""
    x: int
    y: int
    width: int
    height: int


class WindowState(str, Enum):
    """Current display state of a window."""
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    HIDDEN = "hidden"


class InputModifier(str, Enum):
    """Keyboard modifier keys."""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"


class CoordinateSpace(str, Enum):
    """Reference coordinate space for desktop pointer positions."""
    SCREEN = "SCREEN"       # Virtual desktop coordinate space
    MONITOR = "MONITOR"     # Origin relative to specific monitor bounds
    WINDOW = "WINDOW"       # Origin relative to top-left of target window client area


class MouseButton(str, Enum):
    """Mouse pointer buttons."""
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    MIDDLE = "MIDDLE"


class WindowAction(str, Enum):
    """Permitted state operations on application windows."""
    FOCUS = "FOCUS"
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"
    RESTORE = "RESTORE"
    CLOSE = "CLOSE"


class MonitorInfo(BaseModel):
    """Specification and bounds of a connected display monitor."""
    id: int = Field(description="System monitor index")
    name: str = Field(default="Generic Monitor")
    x: int = Field(default=0, description="Virtual X offset")
    y: int = Field(default=0, description="Virtual Y offset")
    width: int = Field(gt=0, description="Width in physical pixels")
    height: int = Field(gt=0, description="Height in physical pixels")
    is_primary: bool = Field(default=False)
    scaling: float = Field(default=1.0, ge=0.5, le=4.0, description="DPI scaling factor")


class ScreenInfo(BaseModel):
    """Overall desktop geometry across all active monitors."""
    virtual_x: int = Field(default=0)
    virtual_y: int = Field(default=0)
    virtual_width: int = Field(gt=0)
    virtual_height: int = Field(gt=0)
    monitors: List[MonitorInfo] = Field(default_factory=list)
    primary_monitor_id: int = Field(default=0)


DisplayInfo = ScreenInfo


class ScreenCaptureRequest(BaseModel):
    """Request envelope for capturing visual screen data."""
    monitor_id: Optional[int] = Field(default=None, description="Monitor index (or None for primary/virtual desktop)")
    region: Optional[Tuple[int, int, int, int]] = Field(default=None, description="(x, y, width, height) bounding box")
    image_format: str = Field(default="png", description="Output format: 'png' or 'jpeg'")
    max_width: Optional[int] = Field(default=None, description="Downscale width limit")
    max_height: Optional[int] = Field(default=None, description="Downscale height limit")
    include_base64: bool = Field(default=False, description="Whether to include in-memory base64 string")


class ScreenCaptureResult(BaseModel):
    """Result of a screen capture operation."""
    image_path: Optional[str] = Field(default=None, description="Relative path within workspace sandbox")
    image_base64: Optional[str] = Field(default=None, description="Base64 data URI if requested")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    format: str = Field(default="png")
    size_bytes: int = Field(ge=0)
    timestamp: float = Field(default_factory=time.time)

    @property
    def file_path(self) -> Optional[str]:
        return self.image_path


class MouseMoveRequest(BaseModel):
    """Request to position the mouse pointer."""
    x: int
    y: int
    coordinate_space: CoordinateSpace = Field(default=CoordinateSpace.SCREEN)
    window_id: Optional[int] = Field(default=None, description="Window handle if coordinate_space is WINDOW")
    monitor_id: Optional[int] = Field(default=None, description="Monitor index if coordinate_space is MONITOR")


class MouseClickRequest(BaseModel):
    """Request to trigger a mouse button click."""
    x: Optional[int] = Field(default=None, description="Optional target X (if omitted, clicks at current cursor pos)")
    y: Optional[int] = Field(default=None, description="Optional target Y")
    button: MouseButton = Field(default=MouseButton.LEFT)
    clicks: int = Field(default=1, ge=1, le=3, description="1=single, 2=double, 3=triple")
    coordinate_space: CoordinateSpace = Field(default=CoordinateSpace.SCREEN)
    window_id: Optional[int] = Field(default=None)
    is_destructive: bool = Field(default=False, description="Flag for clicks requiring high-risk user approval")


class MouseScrollRequest(BaseModel):
    """Request to scroll the mouse wheel."""
    clicks: int = Field(default=1, description="Vertical scroll amount (positive=up, negative=down)")
    delta: Optional[int] = Field(default=None, description="Scroll amount alias")
    direction: Optional[str] = Field(default="down")
    x: Optional[int] = Field(default=None)
    y: Optional[int] = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        if self.delta is not None and "clicks" not in self.__pydantic_fields_set__:
            object.__setattr__(self, "clicks", self.delta)


class KeyboardTypeRequest(BaseModel):
    """Request to type text via keyboard input."""
    text: str = Field(..., max_length=1000, description="Text string to type")
    delay_ms: float = Field(default=10.0, ge=0.0, le=1000.0, description="Delay between key presses")
    is_sensitive: bool = Field(default=False, description="Flag indicating potential secret or password entry")


class KeyboardKeyRequest(BaseModel):
    """Request to press a single discrete key."""
    key: str = Field(..., description="Key identifier from supported allowlist (e.g. 'ENTER', 'ESC', 'TAB')")
    duration_sec: float = Field(default=0.05, ge=0.01, le=5.0)


class KeyboardHotkeyRequest(BaseModel):
    """Request to execute a key combination."""
    keys: List[str] = Field(..., min_length=2, max_length=4, description="Hotkey sequence (e.g. ['CTRL', 'C'])")


class WindowInfo(BaseModel):
    """Metadata describing a desktop application window."""
    handle_id: int = Field(description="Native HWND or virtual window identifier")
    title: str = Field(default="")
    process_name: str = Field(default="")
    process_id: int = Field(default=0)
    x: int = Field(default=0)
    y: int = Field(default=0)
    width: int = Field(default=0)
    height: int = Field(default=0)
    is_foreground: bool = Field(default=False)
    is_minimized: bool = Field(default=False)
    is_maximized: bool = Field(default=False)
    is_visible: bool = Field(default=True)

    @property
    def bounds(self) -> Rect2D:
        return Rect2D(x=self.x, y=self.y, width=self.width, height=self.height)

    @property
    def is_active(self) -> bool:
        return self.is_foreground


class WindowQuery(BaseModel):
    """Criteria for searching and targeting application windows."""
    title: Optional[str] = Field(default=None, description="Direct title search term")
    title_pattern: Optional[str] = Field(default=None, description="Substring or regex pattern for window title")
    process_name: Optional[str] = Field(default=None, description="Exact or partial process name (e.g. 'notepad.exe')")
    exact_match: bool = Field(default=False)

    def model_post_init(self, __context: Any) -> None:
        if self.title and not self.title_pattern:
            object.__setattr__(self, "title_pattern", self.title)


class WindowActionRequest(BaseModel):
    """Request to modify window focus or display state."""
    handle_id: int
    action: WindowAction = Field(default=WindowAction.FOCUS)


class ClipboardReadRequest(BaseModel):
    """Request to read text from system clipboard."""
    max_chars: Optional[int] = Field(default=50000, le=200000)


class ClipboardWriteRequest(BaseModel):
    """Request to copy text to system clipboard."""
    text: str = Field(..., max_length=100000)


class ClipboardFormat(str, Enum):
    """Supported clipboard data formats."""
    TEXT = "text"
    HTML = "html"
    IMAGE = "image"
    FILE_DROP = "file_drop"


class ClipboardData(BaseModel):
    """Detailed clipboard contents payload."""
    format: ClipboardFormat = ClipboardFormat.TEXT
    text: Optional[str] = None
    byte_length: int = 0


class ClipboardClearRequest(BaseModel):
    """Request to purge system clipboard contents."""
    pass


class ClipboardResult(BaseModel):
    """Result of clipboard inspection or write."""
    text: Optional[str] = Field(default=None)
    length: int = Field(default=0)
    success: bool = Field(default=True)


class SystemInfo(BaseModel):
    """Safe, read-only host system telemetry."""
    os_name: str = Field(default="Windows")
    os_version: str = Field(default="")
    architecture: str = Field(default="")
    hostname: str = Field(default="")
    cpu_count: int = Field(default=1)
    memory_total_bytes: int = Field(default=0)
    memory_available_bytes: int = Field(default=0)
    foreground_window_title: Optional[str] = Field(default=None)


SystemInfoResult = SystemInfo


class VerificationMethod(str, Enum):
    """Strategies for verifying desktop action execution."""
    SCREEN_CHANGE = "screen_change"
    WINDOW_TITLE = "window_title"
    WINDOW_FOCUS = "window_focus"
    CLIPBOARD_CONTENT = "clipboard_content"
    TEXT_APPEARANCE = "text_appearance"


class VerificationRequest(BaseModel):
    """Specification for validating an OS action."""
    method: VerificationMethod = VerificationMethod.SCREEN_CHANGE
    expected_value: Optional[Any] = None
    target_window_id: Optional[int] = None
    tolerance: float = 0.05
    timeout_seconds: float = 2.0


class OSVerificationResult(BaseModel):
    """Verification outcome evaluating whether an OS action produced its expected result."""
    verified: bool = Field(..., description="True if action outcome was confirmed")
    observation: str = Field(default="", description="Observation explaining verification outcome")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)


VerificationResult = OSVerificationResult


class OSActionRequest(BaseModel):
    """Audited envelope for an OS automation operation."""
    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:10]}")
    tool_id: str = Field(..., description="Tool ID, e.g. 'os.mouse.click'")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:10]}")
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:10]}")
    timestamp: float = Field(default_factory=time.time)


class OSActionResult(BaseModel):
    """Execution output of an OS automation operation."""
    action_id: str
    tool_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    verification: Optional[OSVerificationResult] = None
