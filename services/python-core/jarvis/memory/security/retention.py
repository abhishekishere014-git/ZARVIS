"""Retention and expiration lifecycle policy for memory records."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jarvis.memory.models import MemoryRecord, MemoryScope, MemoryType


class RetentionPolicy:
    """Computes expiration deadlines and determines pruning eligibility."""

    def __init__(self, default_retention_days: int = 90) -> None:
        self.default_retention_days = default_retention_days

    def compute_expiry(
        self,
        scope: MemoryScope,
        memory_type: MemoryType,
        custom_ttl_seconds: Optional[int] = None,
    ) -> Optional[str]:
        """Calculates ISO 8601 expiration timestamp based on scope and type."""
        now = datetime.now(timezone.utc)

        if custom_ttl_seconds is not None:
            return (now + timedelta(seconds=custom_ttl_seconds)).isoformat()

        # Ephemeral session context expires in 24 hours
        if scope == MemoryScope.SESSION:
            return (now + timedelta(hours=24)).isoformat()

        # Temporary task execution context expires in 7 days
        if memory_type == MemoryType.TASK:
            return (now + timedelta(days=7)).isoformat()

        # Episodic and conversational events follow standard retention window
        if memory_type in (MemoryType.CONVERSATION, MemoryType.EVENT, MemoryType.EPISODIC):
            return (now + timedelta(days=self.default_retention_days)).isoformat()

        # Durable facts, preferences, project architecture, and artifacts do NOT expire automatically
        if memory_type in (MemoryType.FACT, MemoryType.PREFERENCE, MemoryType.PROJECT, MemoryType.ARTIFACT):
            return None

        # Default for summaries
        if memory_type == MemoryType.SUMMARY:
            return (now + timedelta(days=self.default_retention_days)).isoformat()

        return None

    @staticmethod
    def is_expired(record: MemoryRecord) -> bool:
        """Determines if a memory record has passed its expiration deadline."""
        if not record.expires_at:
            return False

        try:
            expiry_dt = datetime.fromisoformat(record.expires_at)
            # Ensure timezone awareness
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= expiry_dt
        except (ValueError, TypeError):
            return False
