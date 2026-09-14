"""Service abstraction and lifecycle contracts."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from jarvis.core.health import ComponentHealth, HealthStatus


class ServiceState(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class BaseService(ABC):
    """Abstract base class for all managed JARVIS services."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._state = ServiceState.CREATED
        self._error: Optional[str] = None

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == ServiceState.RUNNING

    async def start(self) -> None:
        """Start the service."""
        if self._state == ServiceState.RUNNING:
            return
        self._state = ServiceState.STARTING
        try:
            await self._on_start()
            self._state = ServiceState.RUNNING
        except Exception as e:
            self._state = ServiceState.FAILED
            self._error = str(e)
            raise

    async def stop(self) -> None:
        """Stop the service gracefully."""
        if self._state in (ServiceState.STOPPED, ServiceState.CREATED):
            return
        self._state = ServiceState.STOPPING
        try:
            await self._on_stop()
            self._state = ServiceState.STOPPED
        except Exception as e:
            self._state = ServiceState.FAILED
            self._error = str(e)
            raise

    async def health(self) -> ComponentHealth:
        """Report component health state."""
        if self._state == ServiceState.RUNNING:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.HEALTHY,
                details={"state": self._state.value},
            )
        elif self._state == ServiceState.FAILED:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=self._error or "Service in failed state",
                details={"state": self._state.value},
            )
        else:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.DEGRADED,
                message=f"Service is {self._state.value}",
                details={"state": self._state.value},
            )

    @abstractmethod
    async def _on_start(self) -> None:
        """Service-specific startup logic."""
        pass

    @abstractmethod
    async def _on_stop(self) -> None:
        """Service-specific teardown logic."""
        pass
