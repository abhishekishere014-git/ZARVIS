"""Tests for EmbeddingProvider protocol, hash embeddings, and cosine similarity."""

from jarvis.memory.semantic.embeddings import (
    HashEmbeddingProvider,
    MockEmbeddingProvider,
    cosine_similarity,
)


def test_cosine_similarity() -> None:
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    # Identical vectors -> similarity 1.0
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-4
    # Orthogonal vectors -> normalized to 0.5 in [0, 1] range
    assert abs(cosine_similarity(v1, v3) - 0.5) < 1e-4


def test_hash_embedding_provider() -> None:
    provider = HashEmbeddingProvider(dimension=64)
    assert provider.dimension == 64

    vec1 = provider.embed_text("JARVIS artificial intelligence desktop assistant")
    vec2 = provider.embed_text("JARVIS artificial intelligence desktop assistant")
    vec3 = provider.embed_text("Something completely different baking bread recipe")

    assert len(vec1) == 64
    assert len(vec2) == 64
    assert len(vec3) == 64

    # Identical text produces identical vectors
    sim_identical = cosine_similarity(vec1, vec2)
    assert abs(sim_identical - 1.0) < 1e-4

    # Semantically different text has significantly lower similarity
    sim_diff = cosine_similarity(vec1, vec3)
    assert sim_diff < sim_identical


def test_mock_embedding_provider() -> None:
    provider = MockEmbeddingProvider(dimension=32, constant_value=0.2)
    assert provider.dimension == 32
    batch = provider.embed_batch(["text a", "text b"])
    assert len(batch) == 2
    assert len(batch[0]) == 32
