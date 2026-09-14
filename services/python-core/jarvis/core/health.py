"""Health monitoring and diagnostics system."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Optional
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SystemHealthReport(BaseModel):
    status: HealthStatus
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    components: Dict[str, ComponentHealth] = Field(default_factory=dict)


HealthCheckFn = Callable[[], Coroutine[Any, Any, ComponentHealth]]


class HealthRegistry:
    """Central registry for component health checks."""

    def __init__(self) -> None:
        self._probes: Dict[str, HealthCheckFn] = {}

    def register(self, name: str, probe: HealthCheckFn) -> None:
        """Register a component health probe."""
        self._probes[name] = probe

    def unregister(self, name: str) -> None:
        """Remove a component health probe."""
        self._probes.pop(name, None)

    async def check_component(self, name: str) -> ComponentHealth:
        """Execute a single health probe."""
        probe = self._probes.get(name)
        if not probe:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"No health probe registered for '{name}'",
            )
        try:
            return await probe()
        except Exception as exc:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check probe crashed: {str(exc)}",
            )

    async def check_all(self) -> SystemHealthReport:
        """Execute all health probes and aggregate overall status."""
        components: Dict[str, ComponentHealth] = {}
        overall_status = HealthStatus.HEALTHY

        for name in list(self._probes.keys()):
            result = await self.check_component(name)
            components[name] = result
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED

        return SystemHealthReport(status=overall_status, components=components)
