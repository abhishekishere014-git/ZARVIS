"""Unit tests for Phase 10 IPC data models and error contracts."""

import pytest
from jarvis.ipc.errors import (
    IPCConnectionError,
    IPCError,
    IPCHandshakeError,
    IPCMethodNotFoundError,
    IPCOversizedMessageError,
    IPCProtocolError,
    IPCTimeoutError,
)
from jarvis.ipc.models import (
    HandshakePayload,
    HandshakeResponse,
    IPCConnectionState,
    IPCDiagnostics,
)


def test_ipc_connection_state_enum():
    states = [
        IPCConnectionState.DISCONNECTED,
        IPCConnectionState.CONNECTING,
        IPCConnectionState.CONNECTED,
        IPCConnectionState.DEGRADED,
        IPCConnectionState.RECONNECTING,
        IPCConnectionState.STOPPING,
        IPCConnectionState.STOPPED,
        IPCConnectionState.ERROR,
    ]
    for state in states:
        assert isinstance(state.value, str)


def test_handshake_models():
    client_payload = HandshakePayload(
        service="test-gateway",
        version="1.0.0",
        protocol="1.0",
        capabilities=["requests", "events"],
        metadata={"client_id": "test_c1"},
    )
    assert client_payload.service == "test-gateway"
    assert "requests" in client_payload.capabilities

    server_resp = HandshakeResponse(
        service="python-core",
        version="0.1.0",
        session_id="sess_abc123",
    )
    assert server_resp.protocol == "1.0"
    assert "tools" in server_resp.capabilities
    assert server_resp.session_id == "sess_abc123"


def test_ipc_diagnostics():
    diag = IPCDiagnostics(
        state=IPCConnectionState.CONNECTED,
        host="127.0.0.1",
        port=8765,
        connected_clients=2,
        total_requests_handled=150,
        total_events_sent=75,
        uptime_seconds=3600.5,
        active_requests=1,
    )
    d = diag.model_dump()
    assert d["state"] == "CONNECTED"
    assert d["connected_clients"] == 2
    assert d["total_requests_handled"] == 150
    assert d["total_events_sent"] == 75


def test_ipc_error_hierarchy():
    err = IPCMethodNotFoundError("Method 'unknown.action' not found", details={"method": "unknown.action"})
    assert isinstance(err, IPCError)
    assert err.message == "Method 'unknown.action' not found"
    err_dict = err.to_dict()
    assert err_dict["error_type"] == "IPCMethodNotFoundError"
    assert err_dict["details"]["method"] == "unknown.action"

    timeout_err = IPCTimeoutError("Request timed out")
    assert isinstance(timeout_err, IPCError)
