"""Security, privacy, and coordinate safety controls for OS Automation."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from jarvis.os.errors import OSSecurityError
from jarvis.os.models import CoordinateSpace, ScreenInfo, WindowInfo

logger = logging.getLogger("jarvis.os.security")

# Allowed keyboard keys for single key press and hotkey combos
SUPPORTED_KEYS: Set[str] = {
    # Modifiers
    "CTRL", "CONTROL", "ALT", "SHIFT", "WIN", "WINDOWS",
    # Control keys
    "ENTER", "RETURN", "ESC", "ESCAPE", "TAB", "SPACE", "BACKSPACE",
    "DELETE", "DEL", "INSERT", "HOME", "END", "PAGEUP", "PAGEDOWN", "PGUP", "PGDN",
    "UP", "DOWN", "LEFT", "RIGHT",
    "CAPSLOCK", "NUMLOCK", "SCROLLLOCK", "PRINTSCREEN", "PAUSE",
    # Function keys
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    # Letters
    *(chr(i) for i in range(ord("A"), ord("Z") + 1)),
    *(chr(i) for i in range(ord("a"), ord("z") + 1)),
    # Digits
    *(str(i) for i in range(10)),
    # Punctuation
    ".", ",", ";", ":", "-", "_", "=", "+", "/", "\\", "[", "]", "(", ")", "{", "}",
}

# Heuristic patterns for sensitive texts / secrets
SENSITIVE_TEXT_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),
    re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(?:password|passwd|pwd|secret|api_key|token)\s*[:=]\s*\S+", re.IGNORECASE),
]


class OSSecurityManager:
    """Enforces boundaries, coordinate validity, and input privacy on OS interactions."""

    def __init__(
        self,
        temp_dir: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
        screens_temp_dir: Optional[str] = None,
        max_type_length: int = 500,
        max_clipboard_chars: int = 50000,
        max_screen_bytes: int = 10 * 1024 * 1024,
        **kwargs,
    ) -> None:
        if temp_dir is None:
            root = Path(workspace_root) if workspace_root else Path("data/workspace")
            s_dir = screens_temp_dir or "temp/screens"
            temp_dir = root / s_dir
        self.temp_dir = Path(temp_dir).resolve()
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.max_type_length = max_type_length
        self.max_clipboard_chars = max_clipboard_chars
        self.max_screen_bytes = max_screen_bytes
        self._ensure_temp_dir()

    def _ensure_temp_dir(self) -> None:
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create screens temp dir: %s", exc)

    def validate_coordinates(
        self,
        x: int,
        y: int,
        screen_info: ScreenInfo,
        coordinate_space: CoordinateSpace = CoordinateSpace.SCREEN,
        target_window: Optional[WindowInfo] = None,
        target_monitor_id: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Validates coordinates against reference coordinate space and screen boundaries."""
        if coordinate_space == CoordinateSpace.SCREEN:
            min_x = screen_info.virtual_x
            min_y = screen_info.virtual_y
            max_x = min_x + screen_info.virtual_width
            max_y = min_y + screen_info.virtual_height

            if x < min_x or x >= max_x or y < min_y or y >= max_y:
                raise OSSecurityError(
                    f"Screen coordinates ({x}, {y}) out of virtual desktop bounds: [{min_x}, {max_x}) x [{min_y}, {max_y})"
                )
            return x, y

        elif coordinate_space == CoordinateSpace.MONITOR:
            mon = None
            if target_monitor_id is not None:
                for m in screen_info.monitors:
                    if m.id == target_monitor_id:
                        mon = m
                        break
            if not mon and screen_info.monitors:
                mon = screen_info.monitors[0]

            if not mon:
                raise OSSecurityError("No monitor available for MONITOR coordinate space")

            if x < 0 or x >= mon.width or y < 0 or y >= mon.height:
                raise OSSecurityError(
                    f"Monitor coordinates ({x}, {y}) out of monitor {mon.id} bounds ({mon.width}x{mon.height})"
                )
            # Transform to screen coordinate space
            return mon.x + x, mon.y + y

        elif coordinate_space == CoordinateSpace.WINDOW:
            if not target_window:
                raise OSSecurityError("Target window must be provided for WINDOW coordinate space")

            if x < 0 or x >= target_window.width or y < 0 or y >= target_window.height:
                raise OSSecurityError(
                    f"Window coordinates ({x}, {y}) out of window '{target_window.title}' bounds ({target_window.width}x{target_window.height})"
                )
            # Transform to screen coordinate space
            return target_window.x + x, target_window.y + y

        raise OSSecurityError(f"Unsupported coordinate space: {coordinate_space}")

    def validate_key(self, key: str) -> str:
        """Validates a key against the supported keys allowlist."""
        normalized = key.strip().upper()
        if normalized not in SUPPORTED_KEYS and key not in SUPPORTED_KEYS:
            raise OSSecurityError(
                f"Key '{key}' is not in the supported key allowlist. Arbitrary scan codes are prohibited."
            )
        return key if key in SUPPORTED_KEYS else normalized

    def validate_hotkey_sequence(self, keys: List[str]) -> List[str]:
        """Validates a key combination list."""
        if not keys or len(keys) < 2 or len(keys) > 4:
            raise OSSecurityError(f"Hotkey sequence must contain 2 to 4 keys, got {len(keys)}")
        return [self.validate_key(k) for k in keys]

    def validate_text_for_typing(self, text: str) -> None:
        """Validates text input length and checks for prohibited unescaped control chars."""
        if len(text) > self.max_type_length:
            raise OSSecurityError(
                f"Typing text length ({len(text)}) exceeds maximum allowed limit of {self.max_type_length} characters"
            )

    def is_sensitive_text(self, text: str) -> bool:
        """Detects whether text contains API keys, tokens, or credential signatures."""
        for pattern in SENSITIVE_TEXT_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def redact_sensitive_text(self, text: str) -> str:
        """Redacts secrets, API keys, and credential patterns from string."""
        redacted = text
        for pattern in SENSITIVE_TEXT_PATTERNS:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        return redacted

    def resolve_safe_screenshot_path(self, filename: str) -> Path:
        """Resolves a temporary screenshot destination strictly within the sandboxed temp directory."""
        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            raise OSSecurityError(
                f"Path traversal detected in screenshot filename: '{filename}'"
            )
        cleaned = re.sub(r"[^\w\.\-]", "_", filename)
        if not cleaned.lower().endswith((".png", ".jpg", ".jpeg")):
            cleaned += ".png"

        candidate = (self.temp_dir / cleaned).resolve()
        try:
            candidate.relative_to(self.temp_dir)
        except ValueError:
            raise OSSecurityError(f"Screenshot path '{candidate}' escapes sandboxed temp dir '{self.temp_dir}'")

        if candidate.is_symlink():
            raise OSSecurityError(f"Symlinks are prohibited in screenshot files: '{candidate}'")

        return candidate

    def scrub_telemetry_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Scrubs raw image bytes, base64 strings, clipboard content, and typed secrets from telemetry."""
        scrubbed = {}
        for k, v in payload.items():
            if k.lower() in ("image_bytes", "raw_image", "screenshot_bytes", "image_base64"):
                scrubbed[k] = "[OMITTED_SCREENSHOT_DATA]"
            elif k.lower() in ("clipboard_content", "clipboard_text", "typed_text", "password"):
                scrubbed[k] = "[OMITTED_SENSITIVE_TEXT]"
            elif isinstance(v, str):
                scrubbed_str = v
                for pattern in SENSITIVE_TEXT_PATTERNS:
                    scrubbed_str = pattern.sub("[REDACTED_SECRET]", scrubbed_str)
                scrubbed[k] = scrubbed_str
            elif isinstance(v, dict):
                scrubbed[k] = self.scrub_telemetry_payload(v)
            else:
                scrubbed[k] = v
        return scrubbed


# Type alias for clarity
Tuple_Coordinates = tuple[int, int]
