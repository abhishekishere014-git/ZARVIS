"""Clipboard read, write, and clear operations with size enforcement and privacy."""

import logging
from typing import Optional
from jarvis.os.errors import ClipboardError, OSSecurityError
from jarvis.os.models import ClipboardReadRequest, ClipboardResult, ClipboardWriteRequest
from jarvis.os.providers.base import OSProvider
from jarvis.os.security import OSSecurityManager

logger = logging.getLogger("jarvis.os.clipboard.manager")


class ClipboardManager:
    """Controls access to the host system clipboard."""

    def __init__(
        self,
        provider: OSProvider,
        security_manager: OSSecurityManager,
    ) -> None:
        self.provider = provider
        self.security = security_manager

    def read(self, request: Optional[ClipboardReadRequest] = None) -> ClipboardResult:
        """Reads plain text from the clipboard."""
        max_chars = request.max_chars if request and request.max_chars else self.security.max_clipboard_chars
        content = self.provider.read_clipboard()

        if len(content) > max_chars:
            content = content[:max_chars]

        return ClipboardResult(
            text=content,
            length=len(content),
            success=True,
        )

    def write(self, request: ClipboardWriteRequest) -> ClipboardResult:
        """Writes plain text to the clipboard."""
        if len(request.text) > self.security.max_clipboard_chars:
            raise OSSecurityError(
                f"Clipboard write content length ({len(request.text)}) exceeds limit of {self.security.max_clipboard_chars} characters"
            )

        success = self.provider.write_clipboard(request.text)
        return ClipboardResult(
            text=None,  # Do not echo content back
            length=len(request.text),
            success=success,
        )

    def clear(self) -> bool:
        """Clears the clipboard contents."""
        return self.provider.clear_clipboard()
