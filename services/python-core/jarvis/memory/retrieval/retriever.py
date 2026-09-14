"""Hybrid multi-tier memory retriever coordinating working, structured, and semantic stores."""

import logging
import time
from typing import Dict, List, Optional
from jarvis.memory.models import RetrievalQuery, RetrievalResult, ScoredMemory
from jarvis.memory.retrieval.ranking import MemoryRanker
from jarvis.memory.semantic.embeddings import EmbeddingProvider
from jarvis.memory.semantic.store import SemanticMemoryStore
from jarvis.memory.structured.repository import MemoryRepository
from jarvis.memory.working.window import WorkingMemory

logger = logging.getLogger("jarvis.memory.retriever")


class MemoryRetriever:
    """Dispatches search requests across all three tiers and synthesizes ranked results."""

    def __init__(
        self,
        working_memory: WorkingMemory,
        repository: MemoryRepository,
        semantic_store: Optional[SemanticMemoryStore] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        ranker: Optional[MemoryRanker] = None,
    ) -> None:
        self.working_memory = working_memory
        self.repository = repository
        self.semantic_store = semantic_store
        self.embedding_provider = embedding_provider
        self.ranker = ranker or MemoryRanker()

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Executes coordinated hybrid search with deterministic 6-factor ranking."""
        t0 = time.perf_counter()
        degraded = False

        # 1. Gather Working Memory context
        working_messages = self.working_memory.get_recent_messages(limit=10)
        summary_context = self.working_memory.summary

        # 2. Gather candidates from Structured Store
        structured_records = self.repository.search(query)
        candidates: Dict[str, ScoredMemory] = {}

        # Pre-populate candidate map with structured matches
        for rec in structured_records:
            scored = self.ranker.score_record(
                record=rec,
                semantic_score=0.0,
                target_scope=query.scope,
                target_project=query.project_id,
            )
            candidates[rec.id] = scored

        # 3. Gather candidates from Semantic Vector Store
        if self.semantic_store and self.embedding_provider:
            try:
                query_vec = self.embedding_provider.embed_text(query.query)
                knn_matches = self.semantic_store.search_knn(
                    query_vector=query_vec,
                    top_k=query.top_k,
                )
                if self.semantic_store.is_degraded():
                    degraded = True

                for mem_id, sim in knn_matches:
                    if mem_id in candidates:
                        # Re-score with updated semantic similarity
                        rec = candidates[mem_id].record
                        candidates[mem_id] = self.ranker.score_record(
                            record=rec,
                            semantic_score=sim,
                            target_scope=query.scope,
                            target_project=query.project_id,
                        )
                    else:
                        rec = self.repository.get(mem_id)
                        if rec and (query.include_expired or not rec.expires_at):
                            # Enforce project isolation boundary
                            if query.project_id and rec.project_id and rec.project_id != query.project_id:
                                continue
                            candidates[mem_id] = self.ranker.score_record(
                                record=rec,
                                semantic_score=sim,
                                target_scope=query.scope,
                                target_project=query.project_id,
                            )
            except Exception as exc:
                logger.warning("Semantic retrieval failed (%s); falling back to structured results.", exc)
                degraded = True
        else:
            degraded = True

        # Enforce strict project boundary isolation across all candidates
        filtered_candidates = [
            c for c in candidates.values()
            if not (query.project_id and c.record.project_id and c.record.project_id != query.project_id)
        ]

        # Sort combined results by composite final_score descending
        ranked_list = sorted(filtered_candidates, key=lambda x: x.final_score, reverse=True)
        top_results = ranked_list[:query.top_k]

        latency = (time.perf_counter() - t0) * 1000

        return RetrievalResult(
            query=query.query,
            results=top_results,
            working_messages=working_messages,
            summary_context=summary_context,
            degraded=degraded,
            latency_ms=round(latency, 2),
        )
