"""End-to-end integration tests for Phase 10 IPC Bridge."""

import asyncio
from contextlib import asynccontextmanager
import pytest

from jarvis.ipc.framing import parse_json_frame, read_frame, write_frame
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
async def test_end_to_end_multiclient_communication():
    router = IPCRouter()

    async def echo_handler(req: JarvisRequest):
        return {"echo": req.payload.get("msg"), "id_echo": req.id}

    router.register_handler("test.echo", echo_handler)

    async with running_server(router=router) as server:
        num_clients = 3
        clients = []

        for i in range(num_clients):
            r, w = await asyncio.open_connection("127.0.0.1", server.port)
            # Handshake
            await write_frame(
                w,
                {
                    "id": f"hs_{i}",
                    "type": "ipc.handshake",
                    "version": PROTOCOL_VERSION,
                    "payload": {"client_index": i},
                },
            )
            raw = await read_frame(r)
            resp = parse_json_frame(raw)
            assert resp["success"] is True
            clients.append((r, w))

        assert server.connected_clients_count == num_clients

        # Send concurrent requests from all clients
        async def client_worker(client_idx: int, r, w):
            req_id = f"req_c{client_idx}"
            msg_text = f"hello from {client_idx}"
            await write_frame(
                w,
                {
                    "id": req_id,
                    "type": "test.echo",
                    "version": PROTOCOL_VERSION,
                    "payload": {"msg": msg_text},
                },
            )
            raw = await read_frame(r)
            resp = parse_json_frame(raw)
            assert resp["id"] == req_id
            assert resp["success"] is True
            assert resp["payload"]["echo"] == msg_text
            assert resp["payload"]["id_echo"] == req_id

        await asyncio.gather(
            *(client_worker(i, r, w) for i, (r, w) in enumerate(clients))
        )

        # Broadcast event from Python core to all clients
        broadcast_event = JarvisEvent(
            id="global_ev_1",
            type="system.announcement",
            payload={"notice": "maintenance starting soon"},
        )
        sent_count = await server.broadcast_event(broadcast_event)
        assert sent_count == num_clients

        # Verify all clients received broadcast
        for r, w in clients:
            raw = await read_frame(r)
            ev_parsed = parse_json_frame(raw)
            assert ev_parsed["id"] == "global_ev_1"
            assert ev_parsed["type"] == "system.announcement"
            assert ev_parsed["payload"]["notice"] == "maintenance starting soon"

        # Disconnect clients
        for r, w in clients:
            w.close()
            await w.wait_closed()

        await asyncio.sleep(0.05)
        assert server.connected_clients_count == 0
