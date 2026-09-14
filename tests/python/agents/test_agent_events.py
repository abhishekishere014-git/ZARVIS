"""Tests for AgentOrchestrator telemetry events published over AsyncEventBus."""

import asyncio
from pathlib import Path
import pytest
from jarvis.agents.factory import build_agent_system
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.tools.factory import build_tool_system


@pytest.mark.asyncio
async def test_agent_lifecycle_events_published_to_bus(tmp_path: Path) -> None:
    bus = AsyncEventBus()
    await bus.start()

    received_events = []

    async def event_collector(evt: JarvisEvent) -> None:
        received_events.append(evt.type)

    bus.subscribe("*", event_collector)

    tool_system = build_tool_system(workspace_dir=tmp_path, event_bus=bus)
    agent_system = build_agent_system(tool_system=tool_system, event_bus=bus, checkpoint_dir=tmp_path / "checkpoints")

    await agent_system.orchestrator.run("Analyze project risks and requirements")

    # Allow event bus to drain
    await asyncio.sleep(0.05)
    await bus.stop()

    assert "agent.started" in received_events
    assert "agent.planning" in received_events
    assert "agent.plan.created" in received_events
    assert "agent.step.started" in received_events
    assert "agent.step.completed" in received_events
    assert "agent.completed" in received_events
