"""Tests for multi-tier MemoryRetriever."""

from pathlib import Path
from jarvis.memory.models import (
    MemoryRecord,
    MemoryScope,
    MemoryType,
    RetrievalQuery,
)
from jarvis.memory.retrieval.ranking import MemoryRanker
from jarvis.memory.retrieval.retriever import MemoryRetriever
from jarvis.memory.semantic.embeddings import HashEmbeddingProvider
from jarvis.memory.semantic.store import SemanticMemoryStore
from jarvis.memory.structured.database import DatabaseManager
from jarvis.memory.structured.repository import MemoryRepository
from jarvis.memory.working.window import WorkingMemory


def test_hybrid_retrieval(tmp_path: Path) -> None:
    db_mgr = DatabaseManager(db_path=tmp_path / "retrieval_test.db")
    repo = MemoryRepository(db_mgr)
    provider = HashEmbeddingProvider(dimension=64)
    sem_store = SemanticMemoryStore(db_manager=db_mgr, dimension=64)
    working = WorkingMemory()
    ranker = MemoryRanker()

    retriever = MemoryRetriever(
        working_memory=working,
        repository=repo,
        semantic_store=sem_store,
        embedding_provider=provider,
        ranker=ranker,
    )

    # 1. Populate working memory
    working.append_message(role="user", content="What is the current database setup?")

    # 2. Populate structured memory and vector store
    rec1 = MemoryRecord(
        content="SQLite WAL mode is configured for fast local writes",
        memory_type=MemoryType.FACT,
        scope=MemoryScope.PROJECT,
    )
    repo.insert(rec1)
    v1 = provider.embed_text(rec1.content)
    sem_store.index_record(rec1.id, v1)

    rec2 = MemoryRecord(
        content="User loves eating green apples",
        memory_type=MemoryType.FACT,
        scope=MemoryScope.USER,
    )
    repo.insert(rec2)
    v2 = provider.embed_text(rec2.content)
    sem_store.index_record(rec2.id, v2)

    # 3. Retrieve for query 'database configuration'
    query = RetrievalQuery(query="database configuration", top_k=5)
    res = retriever.retrieve(query)

    assert len(res.results) >= 1
    # rec1 (database) must be top ranked over rec2 (green apples)
    top_record = res.results[0].record
    assert top_record.id == rec1.id
    assert len(res.working_messages) == 1
    assert res.latency_ms > 0

    db_mgr.close()
