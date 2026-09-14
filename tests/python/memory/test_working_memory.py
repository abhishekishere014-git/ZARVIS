"""Tests for WorkingBuffer and low-level working memory operations."""

from datetime import datetime, timedelta, timezone
from jarvis.memory.models import WorkingMessage
from jarvis.memory.working.buffer import WorkingBuffer, estimate_tokens


def test_token_estimation() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello") >= 1
    # 40 chars should be approx 10 tokens
    assert 9 <= estimate_tokens("a" * 40) <= 11


def test_buffer_append_and_count() -> None:
    buf = WorkingBuffer()
    buf.append(WorkingMessage(role="user", content="message 1"))
    buf.append(WorkingMessage(role="assistant", content="message 2"))
    assert buf.count() == 2
    assert buf.total_tokens() > 0


def test_buffer_ttl_expiry() -> None:
    buf = WorkingBuffer()
    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()

    buf.append(WorkingMessage(role="user", content="expired", expires_at=past))
    buf.append(WorkingMessage(role="assistant", content="valid", expires_at=future))

    removed = buf.remove_expired()
    assert len(removed) == 1
    assert removed[0].content == "expired"
    assert buf.count() == 1
    assert buf.list()[0].content == "valid"
