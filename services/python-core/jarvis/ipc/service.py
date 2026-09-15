"""IPC Service wrapper integrating IPCServer into JarvisEngine lifecycle."""

from __future__ import annotations

from typing import Optional

from jarvis.core.health import ComponentHealth, HealthStatus
from jarvis.core.service import BaseService
from jarvis.ipc.server import IPCServer


class IPCService(BaseService):
    """Engine-managed service hosting the loopback IPC server."""

    def __init__(self, server: IPCServer, name: str = "ipc_server"):
        super().__init__(name=name)
        self.server = server

    async def _on_start(self) -> None:
        """Start the IPC server."""
        await self.server.start()

    async def _on_stop(self) -> None:
        """Stop the IPC server."""
        await self.server.stop()

    async def health(self) -> ComponentHealth:
        """Report component health with live diagnostics."""
        diag = self.server.get_diagnostics()
        status = HealthStatus.HEALTHY if self.server.is_running else HealthStatus.DEGRADED
        return ComponentHealth(
            name=self.name,
            status=status,
            details=diag.model_dump(),
        )
