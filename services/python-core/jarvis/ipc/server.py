"""TCP IPC Server implementation for Phase 10 Headless IPC Bridge."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional, Set

from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import (
    PROTOCOL_VERSION,
    JarvisEvent,
    JarvisRequest,
    JarvisResponse,
    ProtocolError,
)
from jarvis.ipc.errors import (
    IPCConnectionError,
    IPCHandshakeError,
    IPCOversizedMessageError,
    IPCProtocolError,
)
from jarvis.ipc.framing import parse_json_frame, read_frame, write_frame
from jarvis.ipc.models import (
    HandshakePayload,
    HandshakeResponse,
    IPCConnectionState,
    IPCDiagnostics,
)
from jarvis.ipc.router import IPCRouter

logger = logging.getLogger("jarvis.ipc.server")


class IPCServer:
    """Headless loopback TCP server communicating with Node Gateway over JSON-RPC."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        router: Optional[IPCRouter] = None,
        event_bus: Optional[AsyncEventBus] = None,
        max_message_bytes: int = 10 * 1024 * 1024,
        request_timeout_sec: float = 30.0,
        max_concurrent_requests: int = 100,
    ):
        if host not in ("127.0.0.1", "localhost"):
            raise ValueError(f"Security restriction: IPC Server must bind to loopback, got '{host}'")

        self.host = host
        self.port = port
        self.router = router or IPCRouter()
        self.event_bus = event_bus
        self.max_message_bytes = max_message_bytes
        self.request_timeout_sec = request_timeout_sec
        self.max_concurrent_requests = max_concurrent_requests

        self._server: Optional[asyncio.Server] = None
        self._active_clients: Set[asyncio.StreamWriter] = set()
        self._client_tasks: Set[asyncio.Task] = set()
        self._state = IPCConnectionState.DISCONNECTED

        self._start_time: float = 0.0
        self._active_requests: int = 0
        self._total_requests_handled: int = 0
        self._total_events_sent: int = 0

        # Register diagnostics handler in router
        self.router.register_handler("system.diagnostics", self._handle_diagnostics)

    @property
    def state(self) -> IPCConnectionState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._server.is_serving()

    @property
    def connected_clients_count(self) -> int:
        return len(self._active_clients)

    async def _handle_diagnostics(self, request: JarvisRequest) -> Dict[str, Any]:
        return self.get_diagnostics().model_dump()

    def get_diagnostics(self) -> IPCDiagnostics:
        """Return diagnostic health and performance metrics."""
        uptime = (time.time() - self._start_time) if self._start_time > 0 else 0.0
        return IPCDiagnostics(
            state=self._state,
            host=self.host,
            port=self.port,
            connected_clients=len(self._active_clients),
            total_requests_handled=self._total_requests_handled,
            total_events_sent=self._total_events_sent,
            uptime_seconds=round(uptime, 2),
            active_requests=self._active_requests,
        )

    async def start(self) -> None:
        """Start the loopback TCP IPC server."""
        if self.is_running:
            return

        self._state = IPCConnectionState.CONNECTING
        logger.info("Starting IPC Server on %s:%d...", self.host, self.port)

        try:
            self._server = await asyncio.start_server(
                self._on_client_connected,
                self.host,
                self.port,
            )
            if self.port == 0 and self._server.sockets:
                self.port = self._server.sockets[0].getsockname()[1]
            self._start_time = time.time()
            self._state = IPCConnectionState.CONNECTED
            logger.info("IPC Server listening on %s:%d", self.host, self.port)

            # Subscribe to event bus for event forwarding
            if self.event_bus and getattr(self.event_bus, "is_running", False):
                self.event_bus.subscribe("*", self._on_event_bus_notification)

        except Exception as e:
            self._state = IPCConnectionState.ERROR
            logger.error("Failed to start IPC Server on %s:%d: %s", self.host, self.port, e)
            raise IPCConnectionError(f"Could not bind IPC server to {self.host}:{self.port}: {e}") from e

    async def stop(self) -> None:
        """Gracefully terminate server and close all client connections."""
        self._state = IPCConnectionState.STOPPING
        logger.info("Stopping IPC Server...")

        # Close all active client connections
        for writer in list(self._active_clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._active_clients.clear()

        # Cancel client handling tasks
        for task in list(self._client_tasks):
            if not task.done():
                task.cancel()
        if self._client_tasks:
            await asyncio.gather(*self._client_tasks, return_exceptions=True)
        self._client_tasks.clear()

        # Close server socket
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._state = IPCConnectionState.STOPPED
        logger.info("IPC Server stopped cleanly.")

    def _on_client_connected(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Callback invoked when a new TCP client connects."""
        client_addr = writer.get_extra_info("peername")
        logger.info("New IPC client connection from %s", client_addr)
        task = asyncio.create_task(self._client_loop(reader, writer, client_addr))
        self._client_tasks.add(task)
        task.add_done_callback(self._client_tasks.discard)

    async def _client_loop(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        client_addr: Any,
    ) -> None:
        """Per-client message receiving and execution loop."""
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        is_handshake_done = False

        try:
            while True:
                raw_frame = await read_frame(reader, max_bytes=self.max_message_bytes)
                if raw_frame is None:
                    logger.info("IPC client %s disconnected", client_addr)
                    break

                if not raw_frame.strip():
                    continue

                # Parse frame into JSON
                try:
                    payload_dict = parse_json_frame(raw_frame)
                except IPCProtocolError as proto_err:
                    err_resp = JarvisResponse(
                        id="unknown",
                        type="error.protocol",
                        version=PROTOCOL_VERSION,
                        success=False,
                        error=ProtocolError(
                            code="INVALID_JSON",
                            message=str(proto_err),
                        ),
                    )
                    await write_frame(writer, err_resp)
                    continue

                # 1. Enforce initial handshake
                if not is_handshake_done:
                    if payload_dict.get("type") == "ipc.handshake":
                        req_id = payload_dict.get("id", "handshake_init")
                        version = payload_dict.get("version", "")
                        if version != PROTOCOL_VERSION:
                            err_resp = JarvisResponse(
                                id=req_id,
                                type="ipc.handshake",
                                version=PROTOCOL_VERSION,
                                success=False,
                                error=ProtocolError(
                                    code="PROTOCOL_VERSION_MISMATCH",
                                    message=f"Expected version {PROTOCOL_VERSION}, got '{version}'",
                                ),
                            )
                            await write_frame(writer, err_resp)
                            break

                        # Handshake accepted
                        handshake_resp = HandshakeResponse(session_id=session_id)
                        resp = JarvisResponse(
                            id=req_id,
                            type="ipc.handshake",
                            version=PROTOCOL_VERSION,
                            success=True,
                            payload=handshake_resp.model_dump(),
                        )
                        await write_frame(writer, resp)
                        is_handshake_done = True
                        self._active_clients.add(writer)
                        logger.info("IPC Handshake successful for %s (session=%s)", client_addr, session_id)
                        continue
                    else:
                        # Non-handshake first message rejected
                        err_resp = JarvisResponse(
                            id=payload_dict.get("id", "unknown"),
                            type="error.handshake_required",
                            version=PROTOCOL_VERSION,
                            success=False,
                            error=ProtocolError(
                                code="HANDSHAKE_REQUIRED",
                                message="First message must be 'ipc.handshake'",
                            ),
                        )
                        await write_frame(writer, err_resp)
                        break

                # 2. Parse JarvisRequest
                try:
                    request = JarvisRequest.model_validate(payload_dict)
                except Exception as val_err:
                    err_resp = JarvisResponse(
                        id=payload_dict.get("id", "unknown"),
                        type=payload_dict.get("type", "error.schema"),
                        version=PROTOCOL_VERSION,
                        success=False,
                        error=ProtocolError(
                            code="INVALID_REQUEST_SCHEMA",
                            message=str(val_err),
                        ),
                    )
                    await write_frame(writer, err_resp)
                    continue

                # 3. Check concurrent request limits
                if self._active_requests >= self.max_concurrent_requests:
                    busy_resp = JarvisResponse(
                        id=request.id,
                        type=request.type,
                        version=PROTOCOL_VERSION,
                        success=False,
                        error=ProtocolError(
                            code="SERVER_BUSY",
                            message=f"Server exceeded concurrency limit of {self.max_concurrent_requests}",
                        ),
                    )
                    await write_frame(writer, busy_resp)
                    continue

                # 4. Asynchronously process request
                asyncio.create_task(self._process_request(writer, request))

        except (asyncio.CancelledError, ConnectionResetError):
            pass
        except Exception as exc:
            logger.error("Unhandled error in IPC client loop for %s: %s", client_addr, exc)
        finally:
            self._active_clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _process_request(
        self, writer: asyncio.StreamWriter, request: JarvisRequest
    ) -> None:
        """Execute request under timeout and concurrency limits."""
        self._active_requests += 1
        self._total_requests_handled += 1
        try:
            response = await asyncio.wait_for(
                self.router.dispatch(request),
                timeout=self.request_timeout_sec,
            )
            await write_frame(writer, response)
        except asyncio.TimeoutError:
            logger.warning("IPC request '%s' (id=%s) timed out after %ss", request.type, request.id, self.request_timeout_sec)
            timeout_resp = JarvisResponse(
                id=request.id,
                type=request.type,
                version=PROTOCOL_VERSION,
                success=False,
                error=ProtocolError(
                    code="REQUEST_TIMEOUT",
                    message=f"Request timed out after {self.request_timeout_sec}s",
                ),
            )
            try:
                await write_frame(writer, timeout_resp)
            except Exception:
                pass
        except Exception as exc:
            logger.error("Internal error executing request '%s' (id=%s): %s", request.type, request.id, exc)
            internal_resp = JarvisResponse(
                id=request.id,
                type=request.type,
                version=PROTOCOL_VERSION,
                success=False,
                error=ProtocolError(
                    code="INTERNAL_ERROR",
                    message="Internal execution error",
                ),
            )
            try:
                await write_frame(writer, internal_resp)
            except Exception:
                pass
        finally:
            self._active_requests -= 1

    async def broadcast_event(self, event: JarvisEvent) -> int:
        """Broadcast an event frame to all active connected clients."""
        if not self._active_clients:
            return 0

        sent_count = 0
        dead_clients = set()

        for writer in self._active_clients:
            try:
                await write_frame(writer, event)
                sent_count += 1
            except Exception as e:
                logger.debug("Failed writing event to client, marking dead: %s", e)
                dead_clients.add(writer)

        if dead_clients:
            self._active_clients.difference_update(dead_clients)

        self._total_events_sent += sent_count
        return sent_count

    async def _on_event_bus_notification(self, event: JarvisEvent) -> None:
        """Forward internal AsyncEventBus events to connected IPC clients."""
        await self.broadcast_event(event)
