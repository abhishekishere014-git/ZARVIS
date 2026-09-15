"""Security tests for Phase 10 IPC bridge."""

import asyncio
from contextlib import asynccontextmanager
import pytest

from jarvis.ipc.framing import parse_json_frame, read_frame, write_frame
from jarvis.ipc.router import IPCRouter
from jarvis.ipc.server import IPCServer
from jarvis.protocol.models import PROTOCOL_VERSION, JarvisRequest


@asynccontextmanager
async def running_server(**kwargs):
    server = IPCServer(host="127.0.0.1", port=0, **kwargs)
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_security_loopback_only():
    # Attempting to bind to non-loopback host must raise ValueError
    forbidden_hosts = ["0.0.0.0", "192.168.1.1", "10.0.0.1", "example.com"]
    for host in forbidden_hosts:
        with pytest.raises(ValueError, match="Security restriction"):
            IPCServer(host=host, port=8765)


@pytest.mark.asyncio
async def test_security_malformed_json_graceful():
    async with running_server() as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        # Send invalid JSON
        writer.write(b"not json at all\n")
        await writer.drain()

        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["success"] is False
        assert resp["error"]["code"] == "INVALID_JSON"

        # Ensure server still works afterwards
        handshake_msg = {
            "id": "hs_after_malformed",
            "type": "ipc.handshake",
            "version": PROTOCOL_VERSION,
            "payload": {},
        }
        await write_frame(writer, handshake_msg)
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["id"] == "hs_after_malformed"
        assert resp["success"] is True

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_security_oversized_payload_handling():
    async with running_server(max_message_bytes=512) as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        # Send oversized frame (larger than 512 bytes)
        huge_blob = "A" * 600
        writer.write(f'{{"payload": "{huge_blob}"}}\n'.encode("utf-8"))
        await writer.drain()

        # Connection should close or handle oversized error
        raw = await read_frame(reader)
        # On oversized error, server connection is either dropped or rejected
        assert raw is None or "error" in raw

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_security_sensitive_data_scrubbing_in_router():
    router = IPCRouter()

    async def leaky_handler(req: JarvisRequest):
        secret = "super_secret_api_key_98765"
        raise RuntimeError(f"Authentication failed with key: {secret}")

    router.register_handler("test.auth", leaky_handler)
    async with running_server(router=router) as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        # Handshake
        await write_frame(
            writer,
            {"id": "hs_sec", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
        )
        await read_frame(reader)

        # Request that triggers exception with secret
        await write_frame(
            writer,
            {"id": "req_sec", "type": "test.auth", "version": PROTOCOL_VERSION, "payload": {}},
        )
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)

        assert resp["success"] is False
        # Secret should NOT be in error message
        assert "super_secret_api_key_98765" not in resp["error"]["message"]
        assert "sensitive error condition" in resp["error"]["message"]

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_security_invalid_request_schema():
    async with running_server() as server:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)

        # Handshake
        await write_frame(
            writer,
            {"id": "hs_schema", "type": "ipc.handshake", "version": PROTOCOL_VERSION, "payload": {}},
        )
        await read_frame(reader)

        # Send valid JSON object but invalid JarvisRequest schema (missing required fields like id)
        await write_frame(writer, {"something": "else"})
        raw = await read_frame(reader)
        resp = parse_json_frame(raw)
        assert resp["success"] is False
        assert resp["error"]["code"] == "INVALID_REQUEST_SCHEMA"

        writer.close()
        await writer.wait_closed()
