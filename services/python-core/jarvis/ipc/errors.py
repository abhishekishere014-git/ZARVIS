"""IPC exception hierarchy for Phase 10 Headless IPC Bridge."""

from typing import Any, Dict, Optional


class IPCError(Exception):
    """Base exception for all IPC bridge errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class IPCConnectionError(IPCError):
    """Raised when connection cannot be established or drops unexpectedly."""
    pass


class IPCProtocolError(IPCError):
    """Raised when incoming data violates JSON-RPC v1.0 specifications."""
    pass


class IPCTimeoutError(IPCError):
    """Raised when an IPC request execution times out."""
    pass


class IPCHandshakeError(IPCError):
    """Raised when protocol negotiation or version handshake fails."""
    pass


class IPCOversizedMessageError(IPCError):
    """Raised when incoming message size exceeds configured ceiling."""
    pass


class IPCMethodNotFoundError(IPCError):
    """Raised when requested IPC method/type is unrecognized or unauthorized."""
    pass
