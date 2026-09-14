"""Tests for AsyncEventBus telemetry emission across memory lifecycle operations."""

import asyncio
from pathlib import Path
import pytest
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.memory.manager import MemoryManager


@pytest.mark.asyncio
async def test_memory_lifecycle_event_emission(tmp_path: Path) -> None:
    bus = AsyncEventBus()
    await bus.start()

    emitted_events = []

    async def event_handler(evt: JarvisEvent) -> None:
        emitted_events.append(evt.type)

    bus.subscribe("*", event_handler)

    manager = MemoryManager(db_path=tmp_path / "events_test.db", event_bus=bus)

    # 1. Store triggers write.started, write.completed, embedding.started/completed
    await manager.store(content="Event emission verification fact", source="test")

    # 2. Search triggers search.started, search.completed
    await manager.retrieve("verification")

    # 3. Cleanup triggers cleanup.started, cleanup.completed
    await manager.cleanup_expired()

    # Yield control to allow async event dispatch tasks to complete
    await asyncio.sleep(0.05)

    manager.close()
    await bus.stop()

    assert "memory.write.started" in emitted_events
    assert "memory.write.completed" in emitted_events
    assert "memory.search.started" in emitted_events
    assert "memory.search.completed" in emitted_events
    assert "memory.cleanup.started" in emitted_events
    assert "memory.cleanup.completed" in emitted_events
