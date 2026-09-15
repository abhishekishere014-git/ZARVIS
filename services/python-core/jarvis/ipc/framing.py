"""Stream framing and wire-level serialization for Phase 10 IPC Bridge."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel

from jarvis.ipc.errors import IPCOversizedMessageError, IPCProtocolError


async def read_frame(
    reader: asyncio.StreamReader, max_bytes: int = 10 * 1024 * 1024
) -> Optional[str]:
    """Read a single newline-delimited frame from stream reader.

    Returns None on clean EOF. Raises IPCOversizedMessageError if size limit exceeded.
    """
    try:
        line_bytes = await reader.readline()
    except Exception as e:
        raise IPCProtocolError(f"Failed reading stream frame: {e}") from e

    if not line_bytes:
        return None

    if len(line_bytes) > max_bytes:
        raise IPCOversizedMessageError(
            f"Message size {len(line_bytes)} bytes exceeds limit of {max_bytes} bytes"
        )

    try:
        decoded = line_bytes.decode("utf-8").strip()
    except UnicodeDecodeError as e:
        raise IPCProtocolError(f"Invalid UTF-8 payload in stream frame: {e}") from e

    return decoded


async def write_frame(
    writer: asyncio.StreamWriter, message: Union[str, BaseModel, Dict[str, Any]]
) -> None:
    """Serialize and write a single newline-delimited frame to stream writer."""
    if isinstance(message, BaseModel):
        payload_str = message.model_dump_json()
    elif isinstance(message, dict):
        payload_str = json.dumps(message, ensure_ascii=False)
    else:
        payload_str = str(message).strip()

    data = (payload_str + "\n").encode("utf-8")
    writer.write(data)
    await writer.drain()


def parse_json_frame(raw: str) -> Dict[str, Any]:
    """Parse raw frame string into dictionary with strict error handling."""
    if not raw:
        raise IPCProtocolError("Empty frame payload received")
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise IPCProtocolError("JSON-RPC frame must be a JSON object")
        return parsed
    except json.JSONDecodeError as e:
        raise IPCProtocolError(f"Malformed JSON in frame: {e}") from e
