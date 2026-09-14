"""Asynchronous, fault-isolated event bus for cross-module communication."""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Set, Union
from jarvis.core.health import ComponentHealth, HealthStatus
from jarvis.protocol.models import JarvisEvent

logger = logging.getLogger("jarvis.core.bus")

EventHandler = Callable[[JarvisEvent], Coroutine[Any, Any, None]]


class AsyncEventBus:
    """High-throughput asynchronous event bus with strict fault isolation."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[EventHandler]] = {}
        self._wildcard_subscribers: Set[EventHandler] = set()
        self._active_tasks: Set[asyncio.Task[Any]] = set()
        self._is_running: bool = False
        self._lock = asyncio.Lock()
        self._published_count: int = 0
        self._error_count: int = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self) -> None:
        """Start the event bus."""
        async with self._lock:
            self._is_running = True
            logger.debug("AsyncEventBus started.")

    async def stop(self) -> None:
        """Gracefully drain and cancel in-flight event dispatch tasks."""
        async with self._lock:
            self._is_running = False

        # Wait for or cancel in-flight tasks
        if self._active_tasks:
            logger.debug("Draining %d active event tasks on bus shutdown...", len(self._active_tasks))
            for task in list(self._active_tasks):
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
            self._active_tasks.clear()

        logger.debug("AsyncEventBus stopped.")

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe an async handler to a specific event type, or '*' for all events."""
        if event_type == "*":
            self._wildcard_subscribers.add(handler)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = set()
            self._subscribers[event_type].add(handler)
        logger.debug("Subscribed %s to '%s'", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Unsubscribe a handler. Returns True if removed."""
        if event_type == "*":
            if handler in self._wildcard_subscribers:
                self._wildcard_subscribers.remove(handler)
                return True
            return False
        else:
            handlers = self._subscribers.get(event_type)
            if handlers and handler in handlers:
                handlers.remove(handler)
                if not handlers:
                    del self._subscribers[event_type]
                return True
            return False

    async def publish(self, event: JarvisEvent) -> None:
        """Publish an event to all registered subscribers concurrently with exception isolation."""
        if not self._is_running:
            raise RuntimeError("Cannot publish to a stopped AsyncEventBus.")

        self._published_count += 1

        # Target handlers matching event type + wildcards
        handlers: List[EventHandler] = list(self._subscribers.get(event.type, set()))
        handlers.extend(self._wildcard_subscribers)

        if not handlers:
            return

        # Dispatch each subscriber in its own supervised task for fault isolation
        for handler in handlers:
            task = asyncio.create_task(self._safe_dispatch(handler, event))
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

    async def _safe_dispatch(self, handler: EventHandler, event: JarvisEvent) -> None:
        """Executes a single handler with full error isolation."""
        try:
            await handler(event)
        except asyncio.CancelledError:
            # Handle graceful cancellation during shutdown
            pass
        except Exception as exc:
            self._error_count += 1
            logger.error(
                "Subscriber '%s' failed on event '%s' (ID: %s): %s",
                getattr(handler, "__name__", str(handler)),
                event.type,
                event.id,
                exc,
                exc_info=True,
            )

    async def health(self) -> ComponentHealth:
        """Health check probe for the event bus."""
        status = HealthStatus.HEALTHY if self._is_running else HealthStatus.UNHEALTHY
        return ComponentHealth(
            name="event_bus",
            status=status,
            details={
                "is_running": self._is_running,
                "published_events": self._published_count,
                "subscriber_errors": self._error_count,
                "active_tasks": len(self._active_tasks),
                "event_types_registered": len(self._subscribers),
            },
        )
