"""Strongly-typed Pydantic contracts and data models for JARVIS Tri-Tier Memory Engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid
from pydantic import BaseModel, Field, field_validator


class MemoryType(str, Enum):
    """Classification of durable memory records."""

    CONVERSATION = "conversation"
    FACT = "fact"
    PREFERENCE = "preference"
    TASK = "task"
    PROJECT = "project"
    ARTIFACT = "artifact"
    SUMMARY = "summary"
    EVENT = "event"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryScope(str, Enum):
    """Isolation boundaries preventing cross-domain contamination."""

    SESSION = "session"
    CONVERSATION = "conversation"
    USER = "user"
    PROJECT = "project"
    GLOBAL = "global"


class TrustLevel(str, Enum):
    """Provenance and trustworthiness tier of stored information."""

    SYSTEM = "system"
    USER_VERIFIED = "user_verified"
    MODEL_GENERATED = "model_generated"
    UNTRUSTED = "untrusted"


class EmbeddingStatus(str, Enum):
    """Vector indexing status for semantic retrieval."""

    PENDING = "pending"
    EMBEDDED = "embedded"
    FAILED = "failed"
    SKIPPED = "skipped"


class MemoryRecord(BaseModel):
    """A durable, provenance-tracked unit of knowledge in JARVIS."""

    id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:16]}")
    memory_type: MemoryType = Field(default=MemoryType.FACT)
    content: str = Field(description="Primary textual memory content")
    summary: Optional[str] = Field(default=None, description="Compact summary for quick context expansion")
    scope: MemoryScope = Field(default=MemoryScope.CONVERSATION)
    source: str = Field(default="system", description="Provenance identifier, e.g. agent name, tool, user")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Significance weight (0.0 to 1.0)")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Epistemic certainty (0.0 to 1.0)")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp after which record is eligible for pruning")
    conversation_id: Optional[str] = Field(default=None)
    task_id: Optional[str] = Field(default=None)
    artifact_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_status: EmbeddingStatus = Field(default=EmbeddingStatus.PENDING)
    trust_level: TrustLevel = Field(default=TrustLevel.MODEL_GENERATED)

    @field_validator("content")
    @classmethod
    def validate_content_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Memory record content cannot be empty.")
        return v.strip()


class WorkingMessage(BaseModel):
    """A single transient message stored in Tier 1 Working Memory."""

    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    role: str = Field(description="Message role, e.g. 'system', 'user', 'assistant', 'tool'")
    content: str = Field(description="Raw message text")
    estimated_tokens: int = Field(default=0, ge=0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    priority: int = Field(default=1, ge=0, le=10, description="Eviction priority: higher = preserved longer")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkingMemorySnapshot(BaseModel):
    """Serializable state representation of Tier 1 Working Memory."""

    system_context: Optional[str] = None
    active_task_context: Optional[str] = None
    messages: List[WorkingMessage] = Field(default_factory=list)
    summary: Optional[str] = None
    total_tokens: int = 0
    snapshot_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RetrievalQuery(BaseModel):
    """Search request dispatched across all memory tiers."""

    query: str = Field(description="Search text or semantic query")
    scope: Optional[MemoryScope] = None
    project_id: Optional[str] = None
    conversation_id: Optional[str] = None
    memory_types: Optional[Set[MemoryType]] = None
    min_importance: float = 0.0
    min_confidence: float = 0.0
    top_k: int = Field(default=5, ge=1, le=50)
    include_expired: bool = False
    filters: Dict[str, Any] = Field(default_factory=dict)


class ScoredMemory(BaseModel):
    """A memory record enriched with deterministic hybrid relevance scores."""

    record: MemoryRecord
    final_score: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    scope_score: float = Field(default=0.0, ge=0.0, le=1.0)
    task_score: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    """Consolidated search outcome across working, structured, and semantic stores."""

    query: str
    results: List[ScoredMemory] = Field(default_factory=list)
    working_messages: List[WorkingMessage] = Field(default_factory=list)
    summary_context: Optional[str] = None
    degraded: bool = Field(default=False, description="True if semantic backend fell back to structured queries")
    latency_ms: float = 0.0


class ContextBudget(BaseModel):
    """Token budget boundaries for constructing AI prompts."""

    max_total_tokens: int = Field(default=4096, ge=16)
    reserved_system_tokens: int = Field(default=512, ge=0)
    max_memory_tokens: int = Field(default=1536, ge=8)
    max_working_tokens: int = Field(default=2048, ge=8)


class MemoryMetrics(BaseModel):
    """Observability counters for memory operations."""

    reads_count: int = 0
    writes_count: int = 0
    rejections_count: int = 0
    semantic_queries_count: int = 0
    semantic_fallbacks_count: int = 0
    embedding_success_count: int = 0
    embedding_failure_count: int = 0
    cleanups_count: int = 0
