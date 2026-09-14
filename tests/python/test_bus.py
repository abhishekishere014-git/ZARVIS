import asyncio
import pytest
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent


@pytest.mark.asyncio
async def test_bus_publish_subscribe():
    bus = AsyncEventBus()
    await bus.start()

    received_events = []

    async def on_test_event(event: JarvisEvent):
        received_events.append(event)

    bus.subscribe("test.ping", on_test_event)

    event1 = JarvisEvent(id="1", type="test.ping", payload={"data": "hello"})
    event2 = JarvisEvent(id="2", type="other.type", payload={"data": "world"})

    await bus.publish(event1)
    await bus.publish(event2)

    # Yield control to let async event tasks run
    await asyncio.sleep(0.05)

    assert len(received_events) == 1
    assert received_events[0].id == "1"
    assert received_events[0].payload["data"] == "hello"

    await bus.stop()


@pytest.mark.asyncio
async def test_bus_multiple_and_wildcard_subscribers():
    bus = AsyncEventBus()
    await bus.start()

    specific_received = []
    wildcard_received = []

    async def on_specific(event: JarvisEvent):
        specific_received.append(event)

    async def on_wildcard(event: JarvisEvent):
        wildcard_received.append(event)

    bus.subscribe("service.event", on_specific)
    bus.subscribe("*", on_wildcard)

    evt = JarvisEvent(id="evt-10", type="service.event", payload={"status": "ok"})
    await bus.publish(evt)

    await asyncio.sleep(0.05)

    assert len(specific_received) == 1
    assert len(wildcard_received) == 1

    # Unsubscribe specific
    bus.unsubscribe("service.event", on_specific)
    await bus.publish(JarvisEvent(id="evt-11", type="service.event", payload={"status": "ok"}))

    await asyncio.sleep(0.05)

    assert len(specific_received) == 1  # No new event
    assert len(wildcard_received) == 2  # Received second event

    await bus.stop()


@pytest.mark.asyncio
async def test_bus_subscriber_failure_isolation():
    bus = AsyncEventBus()
    await bus.start()

    healthy_received = []

    async def faulty_subscriber(event: JarvisEvent):
        raise RuntimeError("Catastrophic subscriber failure!")

    async def healthy_subscriber(event: JarvisEvent):
        healthy_received.append(event)

    bus.subscribe("risk.event", faulty_subscriber)
    bus.subscribe("risk.event", healthy_subscriber)

    evt = JarvisEvent(id="risk-1", type="risk.event", payload={"danger": True})

    # Publishing should NOT raise exception despite faulty_subscriber raising
    await bus.publish(evt)
    await asyncio.sleep(0.05)

    assert len(healthy_received) == 1
    health = await bus.health()
    assert health.details["subscriber_errors"] == 1

    await bus.stop()


@pytest.mark.asyncio
async def test_bus_concurrent_publishers():
    bus = AsyncEventBus()
    await bus.start()

    received_counter = 0
    lock = asyncio.Lock()

    async def counter_subscriber(event: JarvisEvent):
        nonlocal received_counter
        async with lock:
            received_counter += 1

    bus.subscribe("concurrent.event", counter_subscriber)

    # Spawn 50 concurrent publishers
    async def publisher(idx: int):
        evt = JarvisEvent(id=str(idx), type="concurrent.event", payload={"idx": idx})
        await bus.publish(evt)

    await asyncio.gather(*(publisher(i) for i in range(50)))
    await asyncio.sleep(0.1)

    assert received_counter == 50

    await bus.stop()
