"""Tier 3: Semantic memory and vector retrieval package."""

from jarvis.memory.semantic.embeddings import (
    EmbeddingProvider,
    HashEmbeddingProvider,
    MockEmbeddingProvider,
    cosine_similarity,
)
from jarvis.memory.semantic.sqlite_vec import is_sqlite_vec_available, load_sqlite_vec_extension
from jarvis.memory.semantic.store import SemanticMemoryStore

__all__ = [
    "EmbeddingProvider",
    "HashEmbeddingProvider",
    "MockEmbeddingProvider",
    "cosine_similarity",
    "is_sqlite_vec_available",
    "load_sqlite_vec_extension",
    "SemanticMemoryStore",
]
