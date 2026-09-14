"""Embedding provider contracts and deterministic vector encoders."""

import hashlib
import math
from typing import List, Protocol, runtime_checkable


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two normalized or arbitrary float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot / (norm_a * norm_b)
    # Clamp to [0.0, 1.0] range
    return max(0.0, min(1.0, (sim + 1.0) / 2.0))


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for vector embedding models."""

    @property
    def dimension(self) -> int:
        ...

    def embed_text(self, text: str) -> List[float]:
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        ...


class HashEmbeddingProvider:
    """Fast, deterministic local embedding provider using rolling feature hashing.

    Requires zero external dependencies or network credentials.
    Generates normalized unit vectors of dimension N.
    """

    def __init__(self, dimension: int = 128) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Encodes text into a normalized float vector via n-gram hashing."""
        if not text or not text.strip():
            return [0.0] * self._dimension

        vec = [0.0] * self._dimension
        words = text.lower().strip().split()

        # Word unigrams and character trigrams
        tokens = list(words)
        for w in words:
            if len(w) >= 3:
                tokens.extend(w[i:i + 3] for i in range(len(w) - 2))

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            vec[idx] += sign

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]

        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Encodes multiple texts sequentially."""
        return [self.embed_text(t) for t in texts]


class MockEmbeddingProvider:
    """Fixed-vector embedding provider designed for predictable unit testing."""

    def __init__(self, dimension: int = 128, constant_value: float = 0.5) -> None:
        self._dimension = dimension
        self.constant_value = constant_value

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        # Hash text length into a slight perturbation for uniqueness
        factor = (len(text) % 10) / 10.0
        vec = [self.constant_value + factor * 0.05] * self._dimension
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
