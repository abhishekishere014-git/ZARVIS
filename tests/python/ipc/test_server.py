"""Unit and integration tests for Phase 10 IPCServer."""

import asyncio
import json
from contextlib import asynccontextmanager
import pytest

from jarvis.ipc.errors import IPCConnectionError
from jarvis.ipc.framing import parse_json_frame, read_frame, write_frame
from jarvis.ipc.models import IPCConnectionState
from jarvis.ipc.router import IPCRouter
from jarvis.ipc.server import IPCServer
from jarvis.protocol.models import PROTOCOL_VERSION, JarvisEvent, JarvisRequest


@asynccontextmanager
async def running_server(**kwargs):
    server = IPCServer(host="127.0.0.1", port=0, **kwargs)
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_server_lifecycle():
    async with running_server() as server:
        assert server.is_running
        assert server.state == IPCConnectionState.CONNECTED
        assert server.port > 0


@pytest.mark.asyncio
async def test_server_rejects_non_loopback():
    with pytest.raises(ValueError, match="Security restriction"):
        IPCServer(host="0.0.0.0", port=8765)

    with pytest.raises(ValueError, match="Security restriction"):
        IPCServer(host="192.168.1.50", port=8765)


@pytest.mark.asyncio
async def test_server_handshake_flow():
    async with running_server() as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        # 1. Successful handshake
        handshake_msg = {
            "id": "hs_1",
            "type": "ipc.handshake",
            "version": PROTOCOL_VERSION,
            "payload": {
                "service": "test-node",
                "version": "1.0.0",
                "protocol": PROTOCOL_VERSION,
                "capabilities": ["requests", "events"],
            },
        }
        await write_frame(writer, handshake_msg)
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["id"] == "hs_1"
        assert resp["success"] is True
        assert "session_id" in resp["payload"]

        # 2. Ping request after handshake
        ping_msg = {
            "id": "ping_1",
            "type": "system.ping",
            "version": PROTOCOL_VERSION,
            "payload": {},
        }
        await write_frame(writer, ping_msg)
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["id"] == "ping_1"
        assert resp["success"] is True
        assert resp["payload"]["status"] == "pong"

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_rejects_first_message_if_not_handshake():
    async with running_server() as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        # Send ping without handshake first
        ping_msg = {
            "id": "ping_premature",
            "type": "system.ping",
            "version": PROTOCOL_VERSION,
            "payload": {},
        }
        await write_frame(writer, ping_msg)
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["success"] is False
        assert resp["error"]["code"] == "HANDSHAKE_REQUIRED"

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_rejects_handshake_version_mismatch():
    async with running_server() as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        handshake_msg = {
            "id": "hs_bad",
            "type": "ipc.handshake",
            "version": "99.99",
            "payload": {"service": "test"},
        }
        await write_frame(writer, handshake_msg)
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["success"] is False
        assert resp["error"]["code"] == "PROTOCOL_VERSION_MISMATCH"

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_broadcast_event():
    async with running_server() as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        # Perform handshake
        await write_frame(
            writer,
            {"id": "hs_ev", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
        )
        await read_frame(reader)
        assert server.connected_clients_count == 1

        # Broadcast event from server
        test_event = JarvisEvent(
            id="ev_1",
            type="test.alert",
            payload={"message": "fire alert"},
        )
        sent = await server.broadcast_event(test_event)
        assert sent == 1

        # Read event on client
        raw = await read_frame(reader)
        event_dict = parse_json_frame(raw)
        assert event_dict["type"] == "test.alert"
        assert event_dict["payload"]["message"] == "fire alert"

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_request_timeout():
    router = IPCRouter()

    async def hanging_handler(req: JarvisRequest):
        await asyncio.sleep(1.0)
        return {"done": True}

    router.register_handler("test.hang", hanging_handler)
    async with running_server(router=router, request_timeout_sec=0.1) as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        await write_frame(
            writer,
            {"id": "hs_t", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
        )
        await read_frame(reader)

        await write_frame(
            writer,
            {"id": "req_timeout", "type": "test.hang", "version": PROTOCOL_VERSION, "payload": {}},
        )
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["id"] == "req_timeout"
        assert resp["success"] is False
        assert resp["error"]["code"] == "REQUEST_TIMEOUT"

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_concurrency_limit():
    router = IPCRouter()

    async def blocker_handler(req: JarvisRequest):
        await asyncio.sleep(0.2)
        return {"ok": True}

    router.register_handler("test.block", blocker_handler)
    async with running_server(router=router, max_concurrent_requests=1) as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        await write_frame(
            writer,
            {"id": "hs_c", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
        )
        await read_frame(reader)

        # Send first request that blocks
        await write_frame(
            writer,
            {"id": "req_1", "type": "test.block", "version": PROTOCOL_VERSION, "payload": {}},
        )
        # Immediately send second request
        await write_frame(
            writer,
            {"id": "req_2", "type": "test.block", "version": PROTOCOL_VERSION, "payload": {}},
        )

        # Read responses
        raw1 = await read_frame(reader)
        resp1 = parse_json_frame(raw1)
        raw2 = await read_frame(reader)
        resp2 = parse_json_frame(raw2)

        responses = {resp1["id"]: resp1, resp2["id"]: resp2}
        assert "req_1" in responses
        assert "req_2" in responses

        writer.close()
        await writer.wait_closed()
