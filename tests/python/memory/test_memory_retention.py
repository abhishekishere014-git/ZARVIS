"""Tests for retention policy, expiration calculation, and automatic pruning."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from jarvis.memory.models import MemoryRecord, MemoryScope, MemoryType
from jarvis.memory.security.retention import RetentionPolicy
from jarvis.memory.structured.database import DatabaseManager
from jarvis.memory.structured.repository import MemoryRepository


def test_retention_policy_expiration_deadlines() -> None:
    policy = RetentionPolicy(default_retention_days=30)

    # Session expires in ~24h
    session_exp = policy.compute_expiry(MemoryScope.SESSION, MemoryType.CONVERSATION)
    assert session_exp is not None

    # Task expires in ~7 days
    task_exp = policy.compute_expiry(MemoryScope.CONVERSATION, MemoryType.TASK)
    assert task_exp is not None

    # Fact and Preference have None (durable)
    fact_exp = policy.compute_expiry(MemoryScope.USER, MemoryType.FACT)
    assert fact_exp is None

    pref_exp = policy.compute_expiry(MemoryScope.USER, MemoryType.PREFERENCE)
    assert pref_exp is None


def test_repository_prune_expired_records(tmp_path: Path) -> None:
    db_mgr = DatabaseManager(db_path=tmp_path / "retention_test.db")
    repo = MemoryRepository(db_mgr)

    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    expired_rec = MemoryRecord(content="Expired session note", expires_at=past)
    valid_rec = MemoryRecord(content="Valid current note", expires_at=future)
    durable_rec = MemoryRecord(content="Durable fact", expires_at=None)

    repo.insert(expired_rec)
    repo.insert(valid_rec)
    repo.insert(durable_rec)
    assert repo.count() == 3

    pruned = repo.prune_expired()
    assert pruned == 1
    assert repo.count() == 2

    assert repo.get(expired_rec.id) is None
    assert repo.get(valid_rec.id) is not None
    assert repo.get(durable_rec.id) is not None

    db_mgr.close()
