"""Performance benchmarks for Working Memory, SQLite queries, and Context Construction."""

import time
from pathlib import Path
import pytest
from jarvis.memory.models import MemoryRecord, RetrievalQuery, RetrievalResult, ScoredMemory
from jarvis.memory.retrieval.context import MemoryContextBuilder
from jarvis.memory.structured.database import DatabaseManager
from jarvis.memory.structured.repository import MemoryRepository
from jarvis.memory.working.window import WorkingMemory


def test_working_memory_latency() -> None:
    wm = WorkingMemory()
    for i in range(50):
        wm.append_message(role="user", content=f"benchmark test message {i}")

    t0 = time.perf_counter()
    _ = wm.get_recent_messages(limit=20)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Target: < 1 ms typical
    assert latency_ms < 5.0, f"Working memory retrieval exceeded limit: {latency_ms:.2f} ms"


def test_sqlite_indexed_query_latency(tmp_path: Path) -> None:
    db_mgr = DatabaseManager(db_path=tmp_path / "perf_test.db")
    repo = MemoryRepository(db_mgr)

    # Seed 100 records
    for i in range(100):
        repo.insert(MemoryRecord(content=f"Database record item {i} regarding performance benchmark"))

    query = RetrievalQuery(query="performance benchmark", top_k=10)

    t0 = time.perf_counter()
    results = repo.search(query)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Target: < 10 ms
    assert latency_ms < 20.0, f"SQLite search latency exceeded limit: {latency_ms:.2f} ms"
    assert len(results) > 0

    db_mgr.close()


def test_context_construction_latency() -> None:
    builder = MemoryContextBuilder()
    scored_memories = [
        ScoredMemory(
            record=MemoryRecord(content=f"Durable fact number {i} for context testing"),
            final_score=0.9 - (i * 0.01),
        )
        for i in range(20)
    ]
    retrieval = RetrievalResult(query="test", results=scored_memories)

    t0 = time.perf_counter()
    context = builder.build_context(retrieval=retrieval)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Target: < 25 ms
    assert latency_ms < 25.0, f"Context builder latency exceeded limit: {latency_ms:.2f} ms"
    assert len(context) > 0
