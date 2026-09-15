"""Unit tests for Phase 10 IPC framing and serialization."""

import asyncio
import pytest
from pydantic import BaseModel

from jarvis.ipc.errors import IPCOversizedMessageError, IPCProtocolError
from jarvis.ipc.framing import parse_json_frame, read_frame, write_frame


class SampleModel(BaseModel):
    name: str
    count: int


@pytest.mark.asyncio
async def test_read_and_write_frame_string():
    reader = asyncio.StreamReader()
    written_data = bytearray()

    class MockWriter:
        def write(self, data: bytes):
            written_data.extend(data)

        async def drain(self):
            pass

    mock_writer = MockWriter()
    await write_frame(mock_writer, '{"test": "hello"}')
    assert written_data == b'{"test": "hello"}\n'

    reader.feed_data(bytes(written_data))
    frame = await read_frame(reader)
    assert frame == '{"test": "hello"}'


@pytest.mark.asyncio
async def test_write_frame_with_pydantic_model_and_dict():
    written = []

    class MockWriter:
        def write(self, data: bytes):
            written.append(data)

        async def drain(self):
            pass

    mock_writer = MockWriter()
    model = SampleModel(name="jarvis", count=42)
    await write_frame(mock_writer, model)
    assert b'"name":"jarvis"' in written[0]
    assert b'"count":42' in written[0]

    await write_frame(mock_writer, {"status": "ok"})
    assert b'{"status": "ok"}\n' in written[1]


@pytest.mark.asyncio
async def test_read_frame_eof():
    reader = asyncio.StreamReader()
    reader.feed_eof()
    frame = await read_frame(reader)
    assert frame is None


@pytest.mark.asyncio
async def test_read_frame_oversized():
    reader = asyncio.StreamReader()
    huge_data = b"x" * 200 + b"\n"
    reader.feed_data(huge_data)
    with pytest.raises(IPCOversizedMessageError):
        await read_frame(reader, max_bytes=100)


def test_parse_json_frame():
    assert parse_json_frame('{"id": "123", "method": "ping"}') == {
        "id": "123",
        "method": "ping",
    }

    with pytest.raises(IPCProtocolError, match="Empty frame"):
        parse_json_frame("")

    with pytest.raises(IPCProtocolError, match="Malformed JSON"):
        parse_json_frame("{not_valid_json")

    with pytest.raises(IPCProtocolError, match="must be a JSON object"):
        parse_json_frame('["array", "not", "object"]')
