"""Tests for deterministic 6-factor hybrid ranking formula."""

from jarvis.memory.config import RankingWeights
from jarvis.memory.models import MemoryRecord, MemoryScope, MemoryType
from jarvis.memory.retrieval.ranking import MemoryRanker


def test_ranking_weights_and_normalization() -> None:
    weights = RankingWeights(
        semantic=0.35,
        recency=0.20,
        importance=0.15,
        confidence=0.10,
        scope=0.10,
        task=0.10,
    )
    ranker = MemoryRanker(weights=weights)

    rec = MemoryRecord(
        content="Important architectural decision",
        importance=1.0,
        confidence=1.0,
        scope=MemoryScope.PROJECT,
        project_id="proj_a",
    )

    scored = ranker.score_record(
        record=rec,
        semantic_score=1.0,
        target_scope=MemoryScope.PROJECT,
        target_project="proj_a",
    )

    # Perfect matches across factors should yield score close to 1.0
    assert 0.90 <= scored.final_score <= 1.0
    assert scored.semantic_score == 1.0
    assert scored.importance_score == 1.0


def test_ranking_cross_project_isolation() -> None:
    ranker = MemoryRanker()

    rec_a = MemoryRecord(
        content="Secret specs of project A",
        scope=MemoryScope.PROJECT,
        project_id="proj_a",
    )

    # Querying with project_id="proj_b" must zero out the scope score
    scored = ranker.score_record(
        record=rec_a,
        semantic_score=0.9,
        target_project="proj_b",
    )
    assert scored.scope_score == 0.0
