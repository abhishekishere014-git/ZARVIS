"""Exponential backoff and retry policy abstraction for AI operations."""

import asyncio
import logging
import random
from typing import Any, Callable, Coroutine, Optional, TypeVar
from jarvis.ai.errors import AICancelledError, AIError

logger = logging.getLogger("jarvis.ai.retry")

T = TypeVar("T")


class RetryPolicy:
    """Configurable exponential backoff policy with jitter."""

    def __init__(
        self,
        max_retries: int = 2,
        initial_delay: float = 0.5,
        max_delay: float = 5.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
    ) -> None:
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    def compute_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Calculate wait delay with backoff, honoring retry_after header if provided."""
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self.max_delay)

        delay = min(self.initial_delay * (self.backoff_multiplier ** attempt), self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay

    async def execute(
        self,
        operation: Callable[[], Coroutine[Any, Any, T]],
        operation_name: str = "ai_operation",
    ) -> T:
        """Executes an async operation with controlled retries on retryable errors."""
        attempt = 0
        while True:
            try:
                return await operation()
            except asyncio.CancelledError:
                raise AICancelledError()
            except AIError as exc:
                if not exc.is_retryable or attempt >= self.max_retries:
                    raise

                retry_after = getattr(exc, "retry_after", None)
                delay = self.compute_delay(attempt, retry_after)
                logger.warning(
                    "Retryable AI error (%s) on '%s'. Retrying in %.2fs (attempt %d/%d)...",
                    exc.__class__.__name__,
                    operation_name,
                    delay,
                    attempt + 1,
                    self.max_retries,
                )
                attempt += 1
                await asyncio.sleep(delay)
