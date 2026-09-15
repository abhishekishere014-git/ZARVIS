"""Unit tests for Phase 10 IPC router and dispatch."""

import asyncio
import pytest

from jarvis.ipc.router import IPCRouter
from jarvis.protocol.models import JarvisRequest


@pytest.mark.asyncio
async def test_router_ping():
    router = IPCRouter()
    assert router.is_method_supported("system.ping")

    req = JarvisRequest(type="system.ping", id="req_ping_1")
    resp = await router.dispatch(req)
    assert resp.id == "req_ping_1"
    assert resp.success is True
    assert resp.payload["status"] == "pong"
    assert resp.payload["server"] == "python-core"


@pytest.mark.asyncio
async def test_router_custom_handler():
    router = IPCRouter()

    async def custom_add(req: JarvisRequest):
        a = req.payload.get("a", 0)
        b = req.payload.get("b", 0)
        return {"sum": a + b}

    router.register_handler("math.add", custom_add)
    assert router.is_method_supported("math.add")

    req = JarvisRequest(type="math.add", id="req_math_1", payload={"a": 10, "b": 25})
    resp = await router.dispatch(req)
    assert resp.id == "req_math_1"
    assert resp.success is True
    assert resp.payload["sum"] == 35

    router.unregister_handler("math.add")
    assert not router.is_method_supported("math.add")


@pytest.mark.asyncio
async def test_router_unknown_method():
    router = IPCRouter()
    req = JarvisRequest(type="nonexistent.method", id="req_404")
    resp = await router.dispatch(req)
    assert resp.id == "req_404"
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == "METHOD_NOT_FOUND"
    assert "nonexistent.method" in resp.error.message


@pytest.mark.asyncio
async def test_router_error_sanitization():
    router = IPCRouter()

    async def leaky_handler(req: JarvisRequest):
        raise ValueError("Invalid secret_token_xyz provided")

    router.register_handler("sensitive.action", leaky_handler)
    req = JarvisRequest(type="sensitive.action", id="req_leak")
    resp = await router.dispatch(req)
    assert resp.success is False
    assert resp.error.code == "EXECUTION_ERROR"
    # Secret must be scrubbed
    assert "secret_token_xyz" not in resp.error.message
    assert "Execution failed with sensitive error condition" in resp.error.message


@pytest.mark.asyncio
async def test_router_concurrent_dispatch():
    router = IPCRouter()

    async def slow_handler(req: JarvisRequest):
        await asyncio.sleep(0.01)
        return {"result": req.payload.get("val")}

    router.register_handler("async.slow", slow_handler)

    requests = [
        JarvisRequest(type="async.slow", id=f"id_{i}", payload={"val": i})
        for i in range(10)
    ]
    responses = await asyncio.gather(*(router.dispatch(req) for req in requests))

    for i, resp in enumerate(responses):
        assert resp.id == f"id_{i}"
        assert resp.payload["result"] == i
