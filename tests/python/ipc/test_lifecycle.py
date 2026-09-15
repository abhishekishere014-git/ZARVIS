"""Lifecycle and cleanup tests for Phase 10 IPC Bridge."""

import asyncio
import pytest

from jarvis.core.health import HealthStatus
from jarvis.ipc.framing import read_frame, write_frame
from jarvis.ipc.models import IPCConnectionState
from jarvis.ipc.server import IPCServer
from jarvis.ipc.service import IPCService
from jarvis.protocol.models import PROTOCOL_VERSION


@pytest.mark.asyncio
async def test_service_lifecycle():
    server = IPCServer(host="127.0.0.1", port=0)
    service = IPCService(server=server, name="ipc_bridge")

    # Initially not running
    health_pre = await service.health()
    assert health_pre.status == HealthStatus.DEGRADED

    # Start service
    await service.start()
    assert service.is_running
    assert server.is_running
    health_running = await service.health()
    assert health_running.status == HealthStatus.HEALTHY
    assert health_running.details["state"] == "CONNECTED"

    # Stop service
    await service.stop()
    assert not service.is_running
    assert not server.is_running
    assert server.state == IPCConnectionState.STOPPED


@pytest.mark.asyncio
async def test_graceful_shutdown_with_connected_clients():
    server = IPCServer(host="127.0.0.1", port=0)
    await server.start()

    # Connect client
    reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
    await write_frame(
        writer,
        {"id": "hs_life", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
    )
    await read_frame(reader)
    assert server.connected_clients_count == 1

    # Stop server while client connected
    await server.stop()
    assert server.connected_clients_count == 0

    # Reading from client reader should return EOF
    eof_read = await read_frame(reader)
    assert eof_read is None

    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_client_clean_disconnect():
    server = IPCServer(host="127.0.0.1", port=0)
    await server.start()

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        await write_frame(
            writer,
            {"id": "hs_disc", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
        )
        await read_frame(reader)
        assert server.connected_clients_count == 1

        # Client closes connection
        writer.close()
        await writer.wait_closed()

        # Give small sleep for server loop to process disconnect
        await asyncio.sleep(0.05)
        assert server.connected_clients_count == 0
    finally:
        await server.stop()
