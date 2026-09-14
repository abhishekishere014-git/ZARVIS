"""Normalized error taxonomy for JARVIS OS Automation."""

from typing import Any, Dict, Optional
from jarvis.core.exceptions import JarvisError


class OSErrorBase(JarvisError):
    """Base exception for all OS automation faults."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)


class ScreenCaptureError(OSErrorBase):
    """Raised when screen or monitor capture fails."""
    pass


class MouseActionError(OSErrorBase):
    """Raised when mouse movement, click, or scroll fails."""
    pass


class KeyboardActionError(OSErrorBase):
    """Raised when keyboard text entry or hotkey fails."""
    pass


class WindowManagementError(OSErrorBase):
    """Raised when window enumeration, focus, or state alteration fails."""
    pass


class WindowNotFoundError(WindowManagementError):
    """Raised when a specified target window could not be located."""
    pass


class WindowAmbiguityError(WindowManagementError):
    """Raised when a window query matches multiple candidate windows and cannot be resolved safely."""
    pass


class ClipboardError(OSErrorBase):
    """Raised when reading or writing to the system clipboard fails."""
    pass


class OSVerificationError(OSErrorBase):
    """Raised when post-action state verification detects that an OS action failed to take effect."""
    pass


class OSPolicyViolationError(OSErrorBase):
    """Raised when an OS action is denied by security policies or safety constraints."""
    pass


class OSActionTimeoutError(OSErrorBase):
    """Raised when an OS operation exceeds configured execution timeout limits."""
    pass


class OSSecurityError(OSErrorBase):
    """Raised when coordinates, paths, or inputs violate desktop security boundaries."""
    pass


class CoordinatesOutOfBoundsError(OSSecurityError):
    """Raised when mouse target coordinates fall outside valid monitor bounds."""
    pass


class KeyNotAllowedError(OSSecurityError):
    """Raised when an unauthorized or blocked hotkey/keystroke is requested."""
    pass


class DirectExecutionDeniedError(OSSecurityError):
    """Raised when arbitrary code or shell injection is attempted."""
    pass


class ResourceExhaustionError(OSSecurityError):
    """Raised when rate limits or safety resource ceilings are exceeded."""
    pass


class OSNotSupportedError(OSErrorBase):
    """Raised when the underlying OS platform is not supported."""
    pass


class OSPermissionDeniedError(OSPolicyViolationError):
    """Raised when user approval or policy permission is denied."""
    pass


class InputDispatchError(OSErrorBase):
    """Raised when low-level hardware or virtual event injection fails."""
    pass


# Taxonomy aliases
OSAutomationError = OSErrorBase
ClipboardAccessError = ClipboardError
WindowOperationError = WindowManagementError
DisplayCaptureError = ScreenCaptureError


__all__ = [
    "ClipboardAccessError",
    "ClipboardError",
    "CoordinatesOutOfBoundsError",
    "DirectExecutionDeniedError",
    "DisplayCaptureError",
    "InputDispatchError",
    "KeyNotAllowedError",
    "KeyboardActionError",
    "MouseActionError",
    "OSActionTimeoutError",
    "OSAutomationError",
    "OSErrorBase",
    "OSNotSupportedError",
    "OSPermissionDeniedError",
    "OSPolicyViolationError",
    "OSSecurityError",
    "OSVerificationError",
    "ResourceExhaustionError",
    "ScreenCaptureError",
    "WindowAmbiguityError",
    "WindowManagementError",
    "WindowNotFoundError",
    "WindowOperationError",
]
