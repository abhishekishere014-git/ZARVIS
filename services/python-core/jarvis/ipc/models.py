"""Data models and connection state contracts for Phase 10 IPC Bridge."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IPCConnectionState(str, Enum):
    """Lifecycle states for IPC connections."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class HandshakePayload(BaseModel):
    """Client handshake information sent on connection start."""
    service: str = "node-gateway"
    version: str = "0.1.0"
    protocol: str = "1.0"
    capabilities: List[str] = Field(default_factory=lambda: ["requests", "events", "heartbeat"])
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HandshakeResponse(BaseModel):
    """Server handshake acknowledgment."""
    service: str = "python-core"
    version: str = "0.1.0"
    protocol: str = "1.0"
    capabilities: List[str] = Field(
        default_factory=lambda: [
            "ai",
            "tools",
            "agents",
            "memory",
            "voice",
            "os",
            "vision",
            "events",
        ]
    )
    session_id: str
    timestamp: float = Field(default_factory=time.time)


class IPCDiagnostics(BaseModel):
    """Health and performance diagnostic report for IPC bridge."""
    state: IPCConnectionState
    host: str
    port: int
    connected_clients: int
    total_requests_handled: int
    total_events_sent: int
    uptime_seconds: float
    active_requests: int
    latency_ms: Optional[float] = None
