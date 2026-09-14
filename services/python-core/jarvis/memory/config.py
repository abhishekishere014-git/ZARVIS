"""Configuration models and defaults for JARVIS Memory Engine."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class WorkingMemoryConfig(BaseModel):
    """Configuration for Tier 1 RAM sliding window buffer."""

    max_messages: int = Field(default=50, ge=1, le=500, description="Max messages in active window")
    max_estimated_tokens: int = Field(default=8192, ge=10, le=65536, description="Token capacity boundary")
    ttl_seconds: Optional[int] = Field(default=None, description="Optional transient message time-to-live")
    max_summary_length: int = Field(default=500, ge=100, le=2000, description="Characters for overflow summaries")
    priority_threshold: int = Field(default=5, ge=0, le=10, description="Minimum priority immune to routine eviction")


class StructuredMemoryConfig(BaseModel):
    """Configuration for Tier 2 SQLite persistent storage."""

    db_path: Optional[Path] = Field(default=None, description="Path to SQLite database file")
    wal_mode: bool = Field(default=True, description="Enable SQLite Write-Ahead Logging")
    busy_timeout_ms: int = Field(default=5000, ge=500, le=30000, description="Busy lock wait timeout")
    retention_days: int = Field(default=90, ge=1, le=3650, description="Default retention for non-durable records")
    auto_vacuum: bool = Field(default=True)


class SemanticMemoryConfig(BaseModel):
    """Configuration for Tier 3 vector similarity retrieval."""

    enabled: bool = Field(default=True, description="Enable semantic vector search")
    vector_dim: int = Field(default=128, ge=8, le=4096, description="Dimension of embedding vectors")
    table_name: str = Field(default="vec_memories")
    distance_metric: str = Field(default="cosine", description="Distance metric ('cosine', 'l2')")
    top_k: int = Field(default=5, ge=1, le=50)
    embedding_provider: str = Field(default="hash", description="Provider identifier: 'hash', 'mock', 'openai', 'gemini'")


class RankingWeights(BaseModel):
    """Normalized weighting coefficients for deterministic hybrid 6-factor scoring."""

    semantic: float = Field(default=0.35, ge=0.0, le=1.0)
    recency: float = Field(default=0.20, ge=0.0, le=1.0)
    importance: float = Field(default=0.15, ge=0.0, le=1.0)
    confidence: float = Field(default=0.10, ge=0.0, le=1.0)
    scope: float = Field(default=0.10, ge=0.0, le=1.0)
    task: float = Field(default=0.10, ge=0.0, le=1.0)


class MemoryConfig(BaseModel):
    """Master configuration container for the Tri-Tier Memory Engine."""

    enabled: bool = Field(default=True)
    working: WorkingMemoryConfig = Field(default_factory=WorkingMemoryConfig)
    structured: StructuredMemoryConfig = Field(default_factory=StructuredMemoryConfig)
    semantic: SemanticMemoryConfig = Field(default_factory=SemanticMemoryConfig)
    weights: RankingWeights = Field(default_factory=RankingWeights)
