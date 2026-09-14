"""Tests for memory domain models, validation, and contracts."""

import pytest
from pydantic import ValidationError
from jarvis.memory.models import (
    EmbeddingStatus,
    MemoryRecord,
    MemoryScope,
    MemoryType,
    RetrievalQuery,
    TrustLevel,
    WorkingMessage,
)


def test_memory_record_defaults() -> None:
    rec = MemoryRecord(content="User prefers dark theme")
    assert rec.id.startswith("mem_")
    assert rec.memory_type == MemoryType.FACT
    assert rec.scope == MemoryScope.CONVERSATION
    assert rec.confidence == 0.8
    assert rec.importance == 0.5
    assert rec.embedding_status == EmbeddingStatus.PENDING
    assert rec.trust_level == TrustLevel.MODEL_GENERATED
    assert rec.content == "User prefers dark theme"


def test_memory_record_empty_content_rejected() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(content="   ")


def test_working_message_model() -> None:
    msg = WorkingMessage(role="user", content="Hello assistant", priority=3)
    assert msg.id.startswith("msg_")
    assert msg.role == "user"
    assert msg.priority == 3


def test_retrieval_query_bounds() -> None:
    q = RetrievalQuery(query="banking project", top_k=10, scope=MemoryScope.PROJECT)
    assert q.query == "banking project"
    assert q.top_k == 10
    assert q.scope == MemoryScope.PROJECT

    with pytest.raises(ValidationError):
        RetrievalQuery(query="test", top_k=0)
