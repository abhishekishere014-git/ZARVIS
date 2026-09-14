"""Tier 1 Working Memory sliding window supervisor."""

from typing import Any, Dict, List, Optional
from jarvis.memory.config import WorkingMemoryConfig
from jarvis.memory.models import WorkingMessage, WorkingMemorySnapshot
from jarvis.memory.working.buffer import WorkingBuffer, estimate_tokens


class WorkingMemory:
    """High-speed in-memory sliding conversation and task state manager."""

    def __init__(self, config: Optional[WorkingMemoryConfig] = None) -> None:
        self.config = config or WorkingMemoryConfig()
        self._buffer = WorkingBuffer()
        self._system_context: Optional[str] = None
        self._active_task_context: Optional[str] = None
        self._summary: Optional[str] = None

    @property
    def system_context(self) -> Optional[str]:
        return self._system_context

    @property
    def active_task_context(self) -> Optional[str]:
        return self._active_task_context

    @property
    def summary(self) -> Optional[str]:
        return self._summary

    def set_system_context(self, context: Optional[str]) -> None:
        """Stores or clears invariant high-priority system context."""
        self._system_context = context

    def set_task_context(self, task_context: Optional[str]) -> None:
        """Stores or clears transient active task state."""
        self._active_task_context = task_context

    def append_message(
        self,
        role: str,
        content: str,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[str] = None,
    ) -> WorkingMessage:
        """Appends a new interaction message and enforces bounded window constraints."""
        msg = WorkingMessage(
            role=role,
            content=content,
            estimated_tokens=estimate_tokens(content),
            priority=priority,
            metadata=metadata or {},
            expires_at=expires_at,
        )
        self._buffer.append(msg)
        self._enforce_bounds()
        return msg

    def get_recent_messages(self, limit: Optional[int] = None) -> List[WorkingMessage]:
        """Retrieves the most recent N messages, pruning expired entries first."""
        self._buffer.remove_expired()
        messages = self._buffer.list()
        if limit is not None and limit > 0:
            return messages[-limit:]
        return messages

    def get_messages_within_tokens(self, token_limit: int) -> List[WorkingMessage]:
        """Retrieves recent messages from newest to oldest up to the token limit."""
        self._buffer.remove_expired()
        messages = self._buffer.list()
        selected: List[WorkingMessage] = []
        accumulated = 0

        # Scan backwards from newest
        for m in reversed(messages):
            if accumulated + m.estimated_tokens > token_limit:
                break
            selected.insert(0, m)
            accumulated += m.estimated_tokens

        return selected

    def total_tokens(self) -> int:
        """Computes total active token count in working buffer."""
        return self._buffer.total_tokens()

    def message_count(self) -> int:
        """Returns count of active messages in working buffer."""
        return self._buffer.count()

    def _enforce_bounds(self) -> None:
        """Enforces message count and token capacity limits via priority-aware eviction."""
        self._buffer.remove_expired()

        while (
            self._buffer.count() > self.config.max_messages
            or self._buffer.total_tokens() > self.config.max_estimated_tokens
        ):
            all_msgs = self._buffer.list()
            if not all_msgs:
                break

            # Locate oldest message with priority below threshold
            eviction_candidate: Optional[WorkingMessage] = None
            for m in all_msgs:
                if m.priority < self.config.priority_threshold:
                    eviction_candidate = m
                    break

            # If all remaining messages are high priority, evict the absolute oldest
            if eviction_candidate is None:
                eviction_candidate = all_msgs[0]

            self._buffer.remove_by_id(eviction_candidate.id)
            self._update_overflow_summary(eviction_candidate)

    def _update_overflow_summary(self, evicted: WorkingMessage) -> None:
        """Maintains a compact progressive summary of evicted working entries."""
        snippet = f"{evicted.role}: {evicted.content[:80]}"
        if not self._summary:
            self._summary = f"Prior conversation: {snippet}"
        else:
            self._summary = f"{self._summary} | {snippet}"

        # Truncate summary if exceeding max length
        if len(self._summary) > self.config.max_summary_length:
            self._summary = "..." + self._summary[-self.config.max_summary_length:]

    def clear(self) -> None:
        """Resets working memory, preserving system context unless cleared explicitly."""
        self._buffer.clear()
        self._active_task_context = None
        self._summary = None

    def snapshot(self) -> WorkingMemorySnapshot:
        """Exports a full state snapshot of Tier 1 Working Memory."""
        return WorkingMemorySnapshot(
            system_context=self._system_context,
            active_task_context=self._active_task_context,
            messages=self._buffer.list(),
            summary=self._summary,
            total_tokens=self._buffer.total_tokens(),
        )

    def restore(self, snapshot: WorkingMemorySnapshot) -> None:
        """Restores working memory state from a snapshot."""
        self._system_context = snapshot.system_context
        self._active_task_context = snapshot.active_task_context
        self._summary = snapshot.summary
        self._buffer.clear()
        for msg in snapshot.messages:
            self._buffer.append(msg)
        self._enforce_bounds()
