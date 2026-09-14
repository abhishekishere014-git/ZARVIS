"""In-memory transient buffer and token estimation for Working Memory."""

import math
from datetime import datetime, timezone
from typing import List, Optional
from jarvis.memory.models import WorkingMessage


def estimate_tokens(text: str) -> int:
    """Fast, deterministic heuristic token estimator (~4 characters per token)."""
    if not text:
        return 0
    # Average token in English and code is ~3.8 to 4 characters
    return max(1, math.ceil(len(text) / 4.0))


class WorkingBuffer:
    """Thread-safe linear storage for transient working messages."""

    def __init__(self) -> None:
        self._messages: List[WorkingMessage] = []

    def append(self, message: WorkingMessage) -> None:
        """Appends a message to the buffer and computes its token footprint."""
        if message.estimated_tokens <= 0:
            message.estimated_tokens = estimate_tokens(message.content)
        self._messages.append(message)

    def total_tokens(self) -> int:
        """Calculates aggregated token usage across all messages."""
        return sum(m.estimated_tokens for m in self._messages)

    def count(self) -> int:
        """Returns total messages in buffer."""
        return len(self._messages)

    def list(self) -> List[WorkingMessage]:
        """Returns a copy of all current messages."""
        return list(self._messages)

    def remove_expired(self) -> List[WorkingMessage]:
        """Prunes messages whose TTL has expired. Returns removed messages."""
        now = datetime.now(timezone.utc)
        valid: List[WorkingMessage] = []
        removed: List[WorkingMessage] = []

        for m in self._messages:
            if m.expires_at:
                try:
                    exp = datetime.fromisoformat(m.expires_at)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if now >= exp:
                        removed.append(m)
                        continue
                except (ValueError, TypeError):
                    pass
            valid.append(m)

        self._messages = valid
        return removed

    def pop_oldest(self, count: int = 1) -> List[WorkingMessage]:
        """Removes and returns the N oldest messages."""
        popped = self._messages[:count]
        self._messages = self._messages[count:]
        return popped

    def remove_by_id(self, message_id: str) -> bool:
        """Removes a specific message by its ID."""
        orig_len = len(self._messages)
        self._messages = [m for m in self._messages if m.id != message_id]
        return len(self._messages) < orig_len

    def clear(self) -> None:
        """Clears all buffered messages."""
        self._messages.clear()
