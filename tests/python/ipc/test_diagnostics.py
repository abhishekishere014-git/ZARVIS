"""Diagnostics and observability tests for Phase 10 IPC Bridge."""

import asyncio
from contextlib import asynccontextmanager
import pytest

from jarvis.ipc.framing import parse_json_frame, read_frame, write_frame
from jarvis.ipc.models import IPCConnectionState
from jarvis.ipc.server import IPCServer
from jarvis.protocol.models import PROTOCOL_VERSION, JarvisEvent


@asynccontextmanager
async def running_server(**kwargs):
    server = IPCServer(host="127.0.0.1", port=0, **kwargs)
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_diagnostics_metrics_tracking():
    async with running_server() as server:
        diag = server.get_diagnostics()
        assert diag.state == IPCConnectionState.CONNECTED
        assert diag.connected_clients == 0
        assert diag.total_requests_handled == 0
        assert diag.total_events_sent == 0
        assert diag.uptime_seconds >= 0.0

        # Connect client
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        await write_frame(
            writer,
            {"id": "hs_diag", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
        )
        await read_frame(reader)

        # Query diagnostics over IPC
        await write_frame(
            writer,
            {"id": "req_diag", "type": "system.diagnostics", "version": PROTOCOL_VERSION, "payload": {}},
        )
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["id"] == "req_diag"
        assert resp["success"] is True
        payload = resp["payload"]
        assert payload["state"] == "CONNECTED"
        assert payload["connected_clients"] == 1
        assert payload["total_requests_handled"] >= 1

        # Broadcast event
        await server.broadcast_event(
            JarvisEvent(id="ev_diag", type="test.evt", payload={"k": "v"})
        )
        await read_frame(reader)

        diag_after = server.get_diagnostics()
        assert diag_after.total_events_sent == 1

        writer.close()
        await writer.wait_closed()
