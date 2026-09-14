"""Unit tests for Vision event bus notifications and telemetry."""

import asyncio
import pytest
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.vision.errors import TargetAmbiguityError
from jarvis.vision.manager import VisionManager
from jarvis.vision.models import (
    BoundingBox,
    ElementType,
    VisualElement,
)
from jarvis.vision.providers.mock import MockVisionProvider


@pytest.mark.asyncio
async def test_vision_event_bus_telemetry():
    event_bus = AsyncEventBus()
    await event_bus.start()

    captured_events: list[JarvisEvent] = []

    async def event_collector(event: JarvisEvent):
        captured_events.append(event)

    event_bus.subscribe("vision.observation.captured", event_collector)
    event_bus.subscribe("vision.target.grounded", event_collector)
    event_bus.subscribe("vision.target.ambiguous", event_collector)

    provider = MockVisionProvider()
    mgr = VisionManager(provider=provider, event_bus=event_bus)

    # 1. Capture and analyze screen -> should emit vision.observation.captured
    await mgr.capture_and_analyze(monitor_index=0, force_refresh=True)
    await asyncio.sleep(0.05)

    assert any(e.type == "vision.observation.captured" for e in captured_events)

    # 2. Resolve clear target -> should emit vision.target.grounded
    await mgr.resolve_target("Google Search", monitor_index=0)
    await asyncio.sleep(0.05)

    assert any(e.type == "vision.target.grounded" for e in captured_events)

    # 3. Resolve ambiguous targets -> should emit vision.target.ambiguous
    provider.add_element(
        VisualElement(
            element_id="btn_dup_1",
            element_type=ElementType.BUTTON,
            bounds=BoundingBox(x=10, y=10, width=50, height=20),
            label="DuplicateButton",
        )
    )
    provider.add_element(
        VisualElement(
            element_id="btn_dup_2",
            element_type=ElementType.BUTTON,
            bounds=BoundingBox(x=10, y=100, width=50, height=20),
            label="DuplicateButton",
        )
    )

    with pytest.raises(TargetAmbiguityError):
        await mgr.resolve_target("DuplicateButton", monitor_index=0, force_refresh=True)

    await asyncio.sleep(0.05)
    assert any(e.type == "vision.target.ambiguous" for e in captured_events)

    await event_bus.stop()
