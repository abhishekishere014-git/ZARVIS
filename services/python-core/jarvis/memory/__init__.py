"""JARVIS Tri-Tier Memory Engine (Working Memory + SQLite Store + Semantic Retrieval)."""

from jarvis.memory.config import (
    MemoryConfig,
    RankingWeights,
    SemanticMemoryConfig,
    StructuredMemoryConfig,
    WorkingMemoryConfig,
)
from jarvis.memory.errors import (
    CapacityExceededError,
    MemoryError,
    MemoryPoisoningError,
    MigrationError,
    SanitizationError,
    ScopeViolationError,
    StorageError,
    VectorStoreError,
)
from jarvis.memory.manager import MemoryManager
from jarvis.memory.models import (
    ContextBudget,
    EmbeddingStatus,
    MemoryMetrics,
    MemoryRecord,
    MemoryScope,
    MemoryType,
    RetrievalQuery,
    RetrievalResult,
    ScoredMemory,
    TrustLevel,
    WorkingMessage,
    WorkingMemorySnapshot,
)
from jarvis.memory.retrieval.context import MemoryContextBuilder
from jarvis.memory.retrieval.ranking import MemoryRanker
from jarvis.memory.retrieval.retriever import MemoryRetriever
from jarvis.memory.security.classifier import MemoryClassifier
from jarvis.memory.security.retention import RetentionPolicy
from jarvis.memory.security.sanitizer import SecretRedactor, sanitize_content, sanitize_metadata
from jarvis.memory.semantic.embeddings import (
    EmbeddingProvider,
    HashEmbeddingProvider,
    MockEmbeddingProvider,
    cosine_similarity,
)
from jarvis.memory.semantic.sqlite_vec import is_sqlite_vec_available, load_sqlite_vec_extension
from jarvis.memory.semantic.store import SemanticMemoryStore
from jarvis.memory.structured.database import DatabaseManager
from jarvis.memory.structured.migrations import MigrationManager
from jarvis.memory.structured.repository import MemoryRepository
from jarvis.memory.working.buffer import WorkingBuffer, estimate_tokens
from jarvis.memory.working.window import WorkingMemory

__all__ = [
    # Manager Facade
    "MemoryManager",
    "MemoryConfig",
    # Models & Enums
    "MemoryRecord",
    "MemoryType",
    "MemoryScope",
    "TrustLevel",
    "EmbeddingStatus",
    "WorkingMessage",
    "WorkingMemorySnapshot",
    "RetrievalQuery",
    "RetrievalResult",
    "ScoredMemory",
    "ContextBudget",
    "MemoryMetrics",
    # Configs
    "WorkingMemoryConfig",
    "StructuredMemoryConfig",
    "SemanticMemoryConfig",
    "RankingWeights",
    # Errors
    "MemoryError",
    "StorageError",
    "SanitizationError",
    "ScopeViolationError",
    "CapacityExceededError",
    "MigrationError",
    "VectorStoreError",
    "MemoryPoisoningError",
    # Tier 1
    "WorkingMemory",
    "WorkingBuffer",
    "estimate_tokens",
    # Tier 2
    "DatabaseManager",
    "MigrationManager",
    "MemoryRepository",
    # Tier 3
    "SemanticMemoryStore",
    "EmbeddingProvider",
    "HashEmbeddingProvider",
    "MockEmbeddingProvider",
    "cosine_similarity",
    "is_sqlite_vec_available",
    "load_sqlite_vec_extension",
    # Retrieval & Ranking
    "MemoryRetriever",
    "MemoryRanker",
    "MemoryContextBuilder",
    # Security
    "SecretRedactor",
    "sanitize_content",
    "sanitize_metadata",
    "MemoryClassifier",
    "RetentionPolicy",
]
