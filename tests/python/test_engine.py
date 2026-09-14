import asyncio
import pytest
from jarvis.config.settings import JarvisSettings
from jarvis.core.engine import JarvisEngine
from jarvis.core.health import ComponentHealth, HealthStatus
from jarvis.core.service import BaseService


class DummyTestService(BaseService):
    def __init__(self, name: str = "dummy_service") -> None:
        super().__init__(name)
        self.started = False
        self.stopped = False

    async def _on_start(self) -> None:
        self.started = True

    async def _on_stop(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_engine_lifecycle():
    settings = JarvisSettings(env="test", vault_backend="memory")
    engine = JarvisEngine(settings=settings)

    service = DummyTestService("test_worker")
    engine.register_service(service)

    assert not engine.is_running
    assert not service.is_running

    # 1. Start engine
    await engine.start()
    assert engine.is_running
    assert service.is_running
    assert service.started is True

    # 2. Check health report
    report = await engine.health_report()
    assert report.status == HealthStatus.HEALTHY
    assert "core" in report.components
    assert "event_bus" in report.components
    assert "vault" in report.components
    assert "test_worker" in report.components

    # 3. Shutdown engine
    await engine.shutdown()
    assert not engine.is_running
    assert not service.is_running
    assert service.stopped is True
