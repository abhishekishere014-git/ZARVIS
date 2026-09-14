import pytest
from jarvis.protocol.models import (
    PROTOCOL_VERSION,
    JarvisEvent,
    JarvisRequest,
    JarvisResponse,
    ProtocolError,
)


def test_python_protocol_valid_request():
    req = JarvisRequest(id="r-1", type="system.ping", payload={"key": "val"})
    assert req.version == PROTOCOL_VERSION
    assert req.id == "r-1"
    assert req.payload["key"] == "val"


def test_python_protocol_valid_response():
    res = JarvisResponse(id="r-1", type="system.ping", success=True, payload={"pong": True})
    assert res.success is True
    assert res.error is None

    err_res = JarvisResponse(
        id="r-2",
        type="system.ping",
        success=False,
        error=ProtocolError(code="TIMEOUT", message="Operation timed out"),
    )
    assert err_res.success is False
    assert err_res.error.code == "TIMEOUT"


def test_python_protocol_invalid_response_contract():
    # success=False but missing error
    with pytest.raises(ValueError, match="Failed response must contain a non-null error object"):
        JarvisResponse(id="r-3", type="system.ping", success=False)

    # success=True but error is provided
    with pytest.raises(ValueError, match="Successful response must not contain an error object"):
        JarvisResponse(
            id="r-4",
            type="system.ping",
            success=True,
            error=ProtocolError(code="ERR", message="Should not be here"),
        )
