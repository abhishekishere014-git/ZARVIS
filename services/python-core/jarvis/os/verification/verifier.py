"""Action verification strategies and post-execution state observation."""

import logging
from typing import Any, Dict, Optional
from jarvis.os.models import OSVerificationResult, WindowInfo
from jarvis.os.providers.base import OSProvider

logger = logging.getLogger("jarvis.os.verification")


class OSActionVerifier:
    """Evaluates post-execution state to confirm OS action effectiveness."""

    def __init__(self, provider: OSProvider) -> None:
        self.provider = provider

    def verify_mouse_position(self, expected_x: int, expected_y: int) -> OSVerificationResult:
        """Verifies that the cursor was successfully positioned."""
        actual_x, actual_y = self.provider.get_cursor_pos()
        matched = (actual_x == expected_x) and (actual_y == expected_y)
        obs = (
            f"Cursor position matches target ({expected_x}, {expected_y})"
            if matched
            else f"Cursor position mismatch: expected ({expected_x}, {expected_y}), got ({actual_x}, {actual_y})"
        )
        return OSVerificationResult(
            verified=matched,
            observation=obs,
            confidence=1.0 if matched else 0.0,
            details={"expected": (expected_x, expected_y), "actual": (actual_x, actual_y)},
        )

    def verify_window_focus(self, target_handle_id: int) -> OSVerificationResult:
        """Verifies that the requested window is currently in the foreground."""
        fg_window = self.provider.get_foreground_window()
        if not fg_window:
            return OSVerificationResult(
                verified=False,
                observation="No foreground window detected",
                confidence=0.0,
            )

        matched = fg_window.handle_id == target_handle_id
        obs = (
            f"Window '{fg_window.title}' (HWND {fg_window.handle_id}) is in foreground."
            if matched
            else f"Window focus mismatch: expected HWND {target_handle_id}, but HWND {fg_window.handle_id} ('{fg_window.title}') is focused."
        )
        return OSVerificationResult(
            verified=matched,
            observation=obs,
            confidence=1.0 if matched else 0.0,
            details={"target_hwnd": target_handle_id, "actual_hwnd": fg_window.handle_id},
        )

    def verify_clipboard_write(self, written_text: str) -> OSVerificationResult:
        """Verifies that clipboard content matches the text written."""
        current = self.provider.read_clipboard()
        matched = current == written_text
        obs = (
            f"Clipboard write verified (length: {len(written_text)})"
            if matched
            else f"Clipboard write mismatch: expected length {len(written_text)}, actual length {len(current)}"
        )
        return OSVerificationResult(
            verified=matched,
            observation=obs,
            confidence=1.0 if matched else 0.0,
            details={"expected_len": len(written_text), "actual_len": len(current)},
        )
