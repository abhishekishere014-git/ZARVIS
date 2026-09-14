"""JARVIS Core Engine orchestrator and service lifecycle supervisor."""

import asyncio
import logging
from typing import Dict, List, Optional
from jarvis.config.settings import JarvisSettings
from jarvis.core.bus import AsyncEventBus
from jarvis.core.exceptions import ConfigurationError, ServiceError
from jarvis.core.health import ComponentHealth, HealthRegistry, HealthStatus, SystemHealthReport
from jarvis.core.service import BaseService
from jarvis.security.vault import SecretVault, get_vault

logger = logging.getLogger("jarvis.core.engine")


class JarvisEngine:
    """Core micro-kernel engine supervising configuration, event bus, and service lifecycles."""

    def __init__(self, settings: Optional[JarvisSettings] = None) -> None:
        self.settings = settings or JarvisSettings()
        self.bus = AsyncEventBus()
        self.health_registry = HealthRegistry()
        self.vault: SecretVault = get_vault(self.settings.vault_backend)
        self._services: Dict[str, BaseService] = {}
        self._is_running: bool = False
        self._shutdown_event = asyncio.Event()

        # Register core probes
        self.health_registry.register("core", self._core_health)
        self.health_registry.register("event_bus", self.bus.health)
        self.health_registry.register("vault", self._vault_health)

    @property
    def is_running(self) -> bool:
        return self._is_running

    def register_service(self, service: BaseService) -> None:
        """Register a managed service with the engine."""
        if service.name in self._services:
            raise ServiceError(f"Service '{service.name}' is already registered.")
        self._services[service.name] = service
        self.health_registry.register(service.name, service.health)
        logger.info("Registered service '%s'", service.name)

    def get_service(self, name: str) -> Optional[BaseService]:
        """Retrieve a registered service by name."""
        return self._services.get(name)

    async def start(self) -> None:
        """Execute structured lifecycle: START -> INIT BUS -> START SERVICES -> HEALTH CHECK."""
        if self._is_running:
            return

        logger.info(
            "Starting JARVIS Engine (Env: %s, Host: %s:%d, Debug: %s)...",
            self.settings.env,
            self.settings.core_host,
            self.settings.core_port,
            self.settings.debug,
        )

        # 1. Start Event Bus
        await self.bus.start()

        # 2. Start all registered services in order
        for name, service in self._services.items():
            logger.info("Starting service '%s'...", name)
            try:
                await service.start()
            except Exception as e:
                logger.critical("Failed to start service '%s': %s", name, e)
                # Cleanup already-started services
                await self.shutdown()
                raise ServiceError(f"Service startup failed for '{name}': {e}") from e

        # 3. Initial Health Check
        report = await self.health_registry.check_all()
        if report.status == HealthStatus.UNHEALTHY:
            logger.warning("Engine started with UNHEALTHY components: %s", report.model_dump())
        else:
            logger.info("Engine health status: %s", report.status.value)

        self._is_running = True
        self._shutdown_event.clear()
        logger.info("JARVIS Engine online and ready.")

    async def run_until_stopped(self) -> None:
        """Block until an asynchronous shutdown is signaled."""
        await self._shutdown_event.wait()

    async def shutdown(self) -> None:
        """Gracefully shut down services in reverse order and stop the event bus."""
        if not self._is_running and self._shutdown_event.is_set():
            return

        logger.info("Initiating JARVIS Engine shutdown...")
        self._is_running = False

        # 1. Stop services in reverse order
        for name, service in reversed(list(self._services.items())):
            logger.info("Stopping service '%s'...", name)
            try:
                await service.stop()
            except Exception as e:
                logger.error("Error stopping service '%s': %s", name, e)

        # 2. Stop event bus
        await self.bus.stop()

        self._shutdown_event.set()
        logger.info("JARVIS Engine shutdown completed.")

    async def health_report(self) -> SystemHealthReport:
        """Retrieve aggregated system health report."""
        return await self.health_registry.check_all()

    async def _core_health(self) -> ComponentHealth:
        return ComponentHealth(
            name="core",
            status=HealthStatus.HEALTHY if self._is_running else HealthStatus.DEGRADED,
            details={
                "env": self.settings.env,
                "is_running": self._is_running,
                "registered_services": list(self._services.keys()),
            },
        )

    async def _vault_health(self) -> ComponentHealth:
        try:
            test_key = "__jarvis_health_probe__"
            self.vault.set_secret(test_key, "probe_val")
            read_back = self.vault.get_secret(test_key)
            self.vault.delete_secret(test_key)
            healthy = (read_back == "probe_val")
            return ComponentHealth(
                name="vault",
                status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
                details={"backend": self.settings.vault_backend},
            )
        except Exception as e:
            return ComponentHealth(
                name="vault",
                status=HealthStatus.UNHEALTHY,
                message=f"Vault probe failed: {e}",
                details={"backend": self.settings.vault_backend},
            )
