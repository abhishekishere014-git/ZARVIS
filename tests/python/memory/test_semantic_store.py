"""Tests for SemanticMemoryStore, vector indexing, KNN retrieval, and fallback behavior."""

from pathlib import Path
from jarvis.memory.semantic.embeddings import HashEmbeddingProvider
from jarvis.memory.semantic.store import SemanticMemoryStore
from jarvis.memory.structured.database import DatabaseManager


def test_semantic_store_index_and_search(tmp_path: Path) -> None:
    db_mgr = DatabaseManager(db_path=tmp_path / "vec_test.db")
    provider = HashEmbeddingProvider(dimension=64)
    store = SemanticMemoryStore(db_manager=db_mgr, dimension=64)

    # 1. Index 3 memories
    v1 = provider.embed_text("Machine learning model training pipeline")
    v2 = provider.embed_text("Deep neural network architectures")
    v3 = provider.embed_text("Italian pizza dough sourdough recipe")

    store.index_record("mem_1", v1)
    store.index_record("mem_2", v2)
    store.index_record("mem_3", v3)

    # 2. Search for AI related query
    query_vec = provider.embed_text("Artificial intelligence training")
    matches = store.search_knn(query_vec, top_k=2)

    assert len(matches) > 0
    top_id, top_sim = matches[0]
    # mem_1 or mem_2 should rank higher than mem_3 (pizza)
    assert top_id in ("mem_1", "mem_2")
    assert top_sim > 0.5

    # 3. Delete record
    deleted = store.delete_record("mem_1")
    assert deleted is True

    db_mgr.close()
