"""Request routing and handler dispatch for Phase 10 Headless IPC Bridge."""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from jarvis.protocol.models import (
    PROTOCOL_VERSION,
    JarvisRequest,
    JarvisResponse,
    ProtocolError,
)
from jarvis.ipc.errors import IPCMethodNotFoundError, IPCProtocolError

logger = logging.getLogger("jarvis.ipc.router")

HandlerFunc = Callable[[JarvisRequest], Awaitable[Dict[str, Any]]]


class IPCRouter:
    """Dispatches incoming JarvisRequests to registered subsystem handlers."""

    def __init__(self):
        self._handlers: Dict[str, HandlerFunc] = {}
        self._register_default_handlers()

    def register_handler(self, method: str, handler: HandlerFunc) -> None:
        """Register a callback handler for a request type."""
        self._handlers[method] = handler
        logger.debug("Registered IPC handler for '%s'", method)

    def unregister_handler(self, method: str) -> None:
        """Remove a registered handler."""
        self._handlers.pop(method, None)

    def is_method_supported(self, method: str) -> bool:
        """Check if request type has a registered handler."""
        return method in self._handlers

    def _register_default_handlers(self) -> None:
        """Register core system handlers."""
        self.register_handler("system.ping", self._handle_ping)
        self.register_handler("system.health", self._handle_health)

    async def _handle_ping(self, request: JarvisRequest) -> Dict[str, Any]:
        return {
            "status": "pong",
            "server": "python-core",
            "protocol": PROTOCOL_VERSION,
            "server_time": time.time(),
        }

    async def _handle_health(self, request: JarvisRequest) -> Dict[str, Any]:
        return {
            "core": "healthy",
            "memory": "unavailable",
            "voice": "unavailable",
            "vision": "unavailable",
            "tools": "unavailable",
            "agent": "unavailable",
            "server_time": time.time(),
        }

    async def dispatch(self, request: JarvisRequest) -> JarvisResponse:
        """Execute request handler and return normalized JarvisResponse."""
        if not self.is_method_supported(request.type):
            logger.warning("Rejected unknown IPC method '%s' (id=%s)", request.type, request.id)
            return JarvisResponse(
                id=request.id,
                type=request.type,
                version=PROTOCOL_VERSION,
                success=False,
                error=ProtocolError(
                    code="METHOD_NOT_FOUND",
                    message=f"No handler registered for method '{request.type}'",
                ),
            )

        handler = self._handlers[request.type]
        try:
            result = await handler(request)
            return JarvisResponse(
                id=request.id,
                type=request.type,
                version=PROTOCOL_VERSION,
                success=True,
                payload=result,
            )
        except Exception as exc:
            logger.error("Error handling IPC request '%s' (id=%s): %s", request.type, request.id, exc)
            # Sanitize error message to avoid secret leaking
            safe_msg = str(exc)
            for secret_word in ["password", "token", "key", "secret", "cvv"]:
                if secret_word in safe_msg.lower():
                    safe_msg = "Execution failed with sensitive error condition"
                    break

            return JarvisResponse(
                id=request.id,
                type=request.type,
                version=PROTOCOL_VERSION,
                success=False,
                error=ProtocolError(
                    code="EXECUTION_ERROR",
                    message=safe_msg,
                ),
            )
