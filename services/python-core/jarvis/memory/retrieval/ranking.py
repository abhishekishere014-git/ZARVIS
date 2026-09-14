"""Deterministic 6-factor hybrid ranking engine for memory retrieval."""

import math
from datetime import datetime, timezone
from typing import Optional
from jarvis.memory.config import RankingWeights
from jarvis.memory.models import MemoryRecord, MemoryScope, ScoredMemory


class MemoryRanker:
    """Calculates deterministic composite relevance scores for candidate memories."""

    def __init__(self, weights: Optional[RankingWeights] = None) -> None:
        self.weights = weights or RankingWeights()

    def compute_recency_score(self, created_at_iso: str, half_life_days: float = 14.0) -> float:
        """Computes exponential decay recency score in [0.0, 1.0]."""
        try:
            dt = datetime.fromisoformat(created_at_iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - dt
            days = max(0.0, delta.total_seconds() / 86400.0)
            # Exponential decay: 0.5 ** (days / half_life)
            return math.exp(-0.693 * days / half_life_days)
        except (ValueError, TypeError):
            return 0.5

    def compute_scope_score(
        self,
        record_scope: MemoryScope,
        target_scope: Optional[MemoryScope],
        record_project: Optional[str] = None,
        target_project: Optional[str] = None,
    ) -> float:
        """Evaluates scope alignment and prevents cross-project leakage."""
        # Cross-project leakage safeguard
        if target_project and record_project and record_project != target_project:
            return 0.0

        if target_scope is None:
            return 0.8

        if record_scope == target_scope:
            return 1.0

        # Global knowledge is generally applicable
        if record_scope == MemoryScope.GLOBAL:
            return 0.85

        # User preferences are relevant in conversational and session scopes
        if record_scope == MemoryScope.USER:
            return 0.80

        return 0.30

    def compute_task_score(self, record_task_id: Optional[str], target_task_id: Optional[str]) -> float:
        """Evaluates active task alignment."""
        if not target_task_id:
            return 0.5
        if record_task_id and record_task_id == target_task_id:
            return 1.0
        return 0.2

    def score_record(
        self,
        record: MemoryRecord,
        semantic_score: float = 0.0,
        target_scope: Optional[MemoryScope] = None,
        target_project: Optional[str] = None,
        target_task_id: Optional[str] = None,
    ) -> ScoredMemory:
        """Calculates deterministic composite score combining all 6 relevance factors."""
        recency = self.compute_recency_score(record.created_at)
        importance = max(0.0, min(1.0, record.importance))
        confidence = max(0.0, min(1.0, record.confidence))
        scope_s = self.compute_scope_score(
            record.scope, target_scope, record.project_id, target_project
        )
        task_s = self.compute_task_score(record.task_id, target_task_id)
        sem_s = max(0.0, min(1.0, semantic_score))

        w = self.weights
        total_w = w.semantic + w.recency + w.importance + w.confidence + w.scope + w.task
        if total_w <= 0.0:
            total_w = 1.0

        raw_score = (
            sem_s * w.semantic
            + recency * w.recency
            + importance * w.importance
            + confidence * w.confidence
            + scope_s * w.scope
            + task_s * w.task
        ) / total_w

        final_score = max(0.0, min(1.0, raw_score))

        return ScoredMemory(
            record=record,
            final_score=round(final_score, 4),
            semantic_score=round(sem_s, 4),
            recency_score=round(recency, 4),
            importance_score=round(importance, 4),
            confidence_score=round(confidence, 4),
            scope_score=round(scope_s, 4),
            task_score=round(task_s, 4),
        )
