"""Keyboard typing, discrete key presses, and hotkey combinations."""

import logging
from typing import List, Optional
from jarvis.os.errors import KeyboardActionError, OSPolicyViolationError
from jarvis.os.models import KeyboardHotkeyRequest, KeyboardKeyRequest, KeyboardTypeRequest
from jarvis.os.providers.base import OSProvider
from jarvis.os.security import OSSecurityManager

logger = logging.getLogger("jarvis.os.input.keyboard")


class KeyboardManager:
    """Controls simulated keyboard text input and keystroke combinations."""

    def __init__(
        self,
        provider: OSProvider,
        security_manager: Optional[OSSecurityManager] = None,
        security: Optional[OSSecurityManager] = None,
        **kwargs,
    ) -> None:
        self.provider = provider
        sec = security or security_manager
        if sec is None:
            sec = OSSecurityManager(screens_temp_dir="temp/screens")
        self.security = sec

    def type_text(self, request: KeyboardTypeRequest, approved: bool = False) -> int:
        """Types unicode string into foreground application."""
        self.security.validate_text_for_typing(request.text)

        is_sensitive = request.is_sensitive or self.security.is_sensitive_text(request.text)
        if is_sensitive and not approved:
            raise OSPolicyViolationError(
                "Typing sensitive text (passwords, tokens, or credentials) requires explicit user approval."
            )

        self.provider.type_text(request.text, delay_ms=request.delay_ms)
        return len(request.text)

    def press_key(self, request: KeyboardKeyRequest) -> str:
        """Presses and releases a single key."""
        valid_key = self.security.validate_key(request.key)
        self.provider.press_key(valid_key, duration_sec=request.duration_sec)
        return valid_key

    def send_hotkey(self, request: KeyboardHotkeyRequest) -> List[str]:
        """Executes a key combination (e.g. CTRL+C, ALT+TAB)."""
        valid_keys = self.security.validate_hotkey_sequence(request.keys)
        self.provider.send_hotkey(valid_keys)
        return valid_keys
