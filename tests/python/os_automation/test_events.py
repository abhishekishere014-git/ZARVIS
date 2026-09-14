"""Tests for OS event telemetry emission on AsyncEventBus and privacy scrubbing."""

import pytest
import asyncio
from jarvis.core.bus import AsyncEventBus
from jarvis.os.manager import OSAutomationManager
from jarvis.os.providers.mock import MockOSProvider
from jarvis.protocol.models import JarvisEvent


@pytest.mark.asyncio
async def test_os_event_emission_and_subscription(tmp_path):
    bus = AsyncEventBus()
    await bus.start()
    try:
        provider = MockOSProvider()
        os_mgr = OSAutomationManager(
            provider=provider,
            event_bus=bus,
            workspace_root=tmp_path,
        )
        received_events = []

        def on_event(evt: JarvisEvent):
            received_events.append(evt)

        bus.subscribe("*", on_event)

        await os_mgr.emit_event(
            event_type="os.mouse.clicked",
            correlation_id="corr_test_123",
            payload={"x": 500, "y": 300, "button": "LEFT"},
        )

        await asyncio.sleep(0.05)

        assert len(received_events) == 1
        evt = received_events[0]
        assert evt.type == "os.mouse.clicked"
        assert evt.correlation_id == "corr_test_123"
        assert evt.payload["x"] == 500
        assert evt.payload["y"] == 300
    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_os_event_privacy_scrubbing(tmp_path):
    bus = AsyncEventBus()
    await bus.start()
    try:
        provider = MockOSProvider()
        os_mgr = OSAutomationManager(
            provider=provider,
            event_bus=bus,
            workspace_root=tmp_path,
        )
        received_events = []

        def on_event(evt: JarvisEvent):
            received_events.append(evt)

        bus.subscribe("*", on_event)

        # Attempt to emit event with sensitive password/token and raw image
        await os_mgr.emit_event(
            event_type="os.keyboard.typed",
            correlation_id="corr_test_privacy",
            payload={
                "text": "password: SecretPassword123",
                "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "clipboard_text": "sk-ant-api03-abcdefghijklmnopqrstu",
            },
        )

        await asyncio.sleep(0.05)

        assert len(received_events) == 1
        evt = received_events[0]
        # Check that secrets and image base64 were stripped or redacted
        payload_str = str(evt.payload)
        assert "SecretPassword123" not in payload_str
        assert "sk-ant-api03" not in payload_str
    finally:
        await bus.stop()
