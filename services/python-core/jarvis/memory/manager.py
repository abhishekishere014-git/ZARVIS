"""Unified facade supervising the Tri-Tier Memory Engine."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent
from jarvis.memory.config import MemoryConfig
from jarvis.memory.errors import CapacityExceededError, MemoryPoisoningError, SanitizationError
from jarvis.memory.models import (
    ContextBudget,
    EmbeddingStatus,
    MemoryMetrics,
    MemoryRecord,
    MemoryScope,
    MemoryType,
    RetrievalQuery,
    RetrievalResult,
    TrustLevel,
    WorkingMessage,
)
from jarvis.memory.retrieval.context import MemoryContextBuilder
from jarvis.memory.retrieval.ranking import MemoryRanker
from jarvis.memory.retrieval.retriever import MemoryRetriever
from jarvis.memory.security.classifier import MemoryClassifier
from jarvis.memory.security.retention import RetentionPolicy
from jarvis.memory.security.sanitizer import sanitize_content, sanitize_metadata
from jarvis.memory.semantic.embeddings import EmbeddingProvider, HashEmbeddingProvider
from jarvis.memory.semantic.store import SemanticMemoryStore
from jarvis.memory.structured.database import DatabaseManager
from jarvis.memory.structured.repository import MemoryRepository
from jarvis.memory.working.window import WorkingMemory

logger = logging.getLogger("jarvis.memory.manager")


class MemoryManager:
    """Master controller orchestrating Tier 1 (Working), Tier 2 (Structured), and Tier 3 (Semantic) memory."""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        db_path: Optional[Path] = None,
        event_bus: Optional[AsyncEventBus] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ) -> None:
        self.config = config or MemoryConfig()
        self.event_bus = event_bus
        self.metrics = MemoryMetrics()

        # 1. Tier 1: Working Memory
        self.working = WorkingMemory(self.config.working)

        # 2. Tier 2: SQLite Structured Storage
        target_db = db_path or self.config.structured.db_path
        self.db_manager = DatabaseManager(
            db_path=target_db,
            wal_mode=self.config.structured.wal_mode,
            busy_timeout_ms=self.config.structured.busy_timeout_ms,
        )
        self.repository = MemoryRepository(self.db_manager)

        # 3. Tier 3: Semantic Vector Storage
        self.embedding_provider = embedding_provider or HashEmbeddingProvider(
            dimension=self.config.semantic.vector_dim
        )
        self.semantic_store: Optional[SemanticMemoryStore] = None
        if self.config.semantic.enabled:
            self.semantic_store = SemanticMemoryStore(
                db_manager=self.db_manager,
                dimension=self.config.semantic.vector_dim,
                table_name=self.config.semantic.table_name,
            )

        # Supporting subsystems
        self.retention_policy = RetentionPolicy(default_retention_days=self.config.structured.retention_days)
        self.ranker = MemoryRanker(weights=self.config.weights)
        self.retriever = MemoryRetriever(
            working_memory=self.working,
            repository=self.repository,
            semantic_store=self.semantic_store,
            embedding_provider=self.embedding_provider,
            ranker=self.ranker,
        )
        self.context_builder = MemoryContextBuilder()

    async def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publishes memory lifecycle events onto the AsyncEventBus safely."""
        if not self.event_bus or not self.event_bus.is_running:
            return

        # Ensure secrets are not leaked into telemetry events
        safe_payload = sanitize_metadata(payload)
        event = JarvisEvent(
            id=f"evt_mem_{int(time.time() * 1000)}",
            type=event_type,
            payload=safe_payload,
        )
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to publish memory telemetry '%s': %s", event_type, exc)

    # -------------------------------------------------------------------------
    # Working Memory Surface
    # -------------------------------------------------------------------------

    def append_working_message(
        self,
        role: str,
        content: str,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkingMessage:
        """Sanitizes and appends an interaction to Tier 1 Working Memory."""
        clean_content = sanitize_content(content)
        clean_meta = sanitize_metadata(metadata or {})
        return self.working.append_message(
            role=role,
            content=clean_content,
            priority=priority,
            metadata=clean_meta,
        )

    def get_working_messages(self, limit: Optional[int] = None) -> List[WorkingMessage]:
        return self.working.get_recent_messages(limit=limit)

    def set_system_context(self, context: Optional[str]) -> None:
        self.working.set_system_context(sanitize_content(context) if context else None)

    def set_task_context(self, context: Optional[str]) -> None:
        self.working.set_task_context(sanitize_content(context) if context else None)

    # -------------------------------------------------------------------------
    # Write Pipeline
    # -------------------------------------------------------------------------

    async def store(
        self,
        content: str,
        source: str = "user",
        memory_type: Optional[MemoryType] = None,
        scope: Optional[MemoryScope] = None,
        importance: Optional[float] = None,
        confidence: Optional[float] = None,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        custom_ttl_seconds: Optional[int] = None,
    ) -> MemoryRecord:
        """Executes the complete multi-stage persistent write pipeline.

        Pipeline:
        1. Normalize & Validate non-empty
        2. Sanitize (Redact all credentials/keys)
        3. Classify & Detect Prompt Injection (Assign Trust Level & Memory Type)
        4. Calculate Retention Expiry
        5. Persist to Tier 2 SQLite
        6. Compute & Index Tier 3 Vector Embedding
        7. Emit Telemetry Event
        """
        self.metrics.writes_count += 1
        t0 = time.perf_counter()

        await self._emit_event("memory.write.started", {"source": source})

        try:
            # 1. Normalize
            raw_content = content.strip() if content else ""
            if not raw_content:
                raise ValueError("Cannot persist empty memory content.")

            # 2. Sanitize secrets
            clean_content = sanitize_content(raw_content)
            clean_metadata = sanitize_metadata(metadata or {})

            # 3. Classify & Check for Injection
            cls_type, cls_scope, trust, base_imp = MemoryClassifier.classify(
                content=clean_content,
                source=source,
                explicit_type=memory_type,
                explicit_scope=scope,
            )

            final_type = memory_type or cls_type
            final_scope = scope or cls_scope
            final_importance = importance if importance is not None else base_imp
            final_confidence = confidence if confidence is not None else (1.0 if trust == TrustLevel.USER_VERIFIED else 0.8)

            # 4. Retention
            expires_at = self.retention_policy.compute_expiry(
                scope=final_scope,
                memory_type=final_type,
                custom_ttl_seconds=custom_ttl_seconds,
            )

            # 5. Build Record & Persist
            record = MemoryRecord(
                memory_type=final_type,
                content=clean_content,
                scope=final_scope,
                source=source,
                importance=final_importance,
                confidence=final_confidence,
                expires_at=expires_at,
                conversation_id=conversation_id,
                task_id=task_id,
                artifact_id=artifact_id,
                project_id=project_id,
                metadata=clean_metadata,
                embedding_status=EmbeddingStatus.PENDING,
                trust_level=trust,
            )

            saved = self.repository.insert(record)

            # 6. Semantic Vector Indexing
            if self.semantic_store and self.embedding_provider:
                await self._emit_event("memory.embedding.started", {"memory_id": saved.id})
                try:
                    vector = self.embedding_provider.embed_text(saved.content)
                    self.semantic_store.index_record(saved.id, vector, metadata={"scope": saved.scope.value})
                    saved.embedding_status = EmbeddingStatus.EMBEDDED
                    self.repository.update(saved)
                    self.metrics.embedding_success_count += 1
                    await self._emit_event("memory.embedding.completed", {"memory_id": saved.id})
                except Exception as emb_exc:
                    logger.warning("Vector embedding failed for record '%s': %s", saved.id, emb_exc)
                    saved.embedding_status = EmbeddingStatus.FAILED
                    self.repository.update(saved)
                    self.metrics.embedding_failure_count += 1

            latency = (time.perf_counter() - t0) * 1000
            await self._emit_event(
                "memory.write.completed",
                {"memory_id": saved.id, "scope": saved.scope.value, "latency_ms": latency},
            )
            return saved

        except (MemoryPoisoningError, ValueError, SanitizationError) as err:
            self.metrics.rejections_count += 1
            await self._emit_event("memory.write.rejected", {"reason": str(err)})
            raise

    # -------------------------------------------------------------------------
    # Retrieval & Context Building
    # -------------------------------------------------------------------------

    async def retrieve(self, query: str | RetrievalQuery) -> RetrievalResult:
        """Dispatches hybrid search across Working, Structured, and Semantic memory."""
        self.metrics.reads_count += 1
        ret_query = RetrievalQuery(query=query) if isinstance(query, str) else query

        await self._emit_event("memory.search.started", {"query": ret_query.query})

        if self.semantic_store:
            self.metrics.semantic_queries_count += 1
            if self.semantic_store.is_degraded():
                self.metrics.semantic_fallbacks_count += 1

        result = self.retriever.retrieve(ret_query)

        await self._emit_event(
            "memory.search.completed",
            {"query": ret_query.query, "results_count": len(result.results), "degraded": result.degraded},
        )
        return result

    def build_context_for_prompt(
        self,
        retrieval: RetrievalResult,
        task_context: Optional[str] = None,
        budget: Optional[ContextBudget] = None,
    ) -> str:
        """Assembles bounded system prompt context containing relevant memories."""
        return self.context_builder.build_context(
            retrieval=retrieval,
            task_context=task_context or self.working.active_task_context,
            system_context=self.working.system_context,
            custom_budget=budget,
        )

    # -------------------------------------------------------------------------
    # Memory Consolidation & Lifecycle Maintenance
    # -------------------------------------------------------------------------

    async def consolidate(self) -> int:
        """Evaluates working memory messages and promotes memoryworthy facts into structured storage."""
        await self._emit_event("memory.consolidation.started", {})
        messages = self.working.get_recent_messages()
        promoted = 0

        for msg in messages:
            if MemoryClassifier.is_memory_worthy(msg.content):
                try:
                    await self.store(
                        content=msg.content,
                        source=f"working_memory.{msg.role}",
                        scope=MemoryScope.CONVERSATION,
                    )
                    promoted += 1
                except Exception as exc:
                    logger.debug("Skipped consolidating message: %s", exc)

        await self._emit_event("memory.consolidation.completed", {"promoted_count": promoted})
        return promoted

    async def cleanup_expired(self) -> int:
        """Prunes expired transient records from SQLite storage."""
        await self._emit_event("memory.cleanup.started", {})
        deleted = self.repository.prune_expired()
        self.metrics.cleanups_count += 1
        await self._emit_event("memory.cleanup.completed", {"deleted_count": deleted})
        return deleted

    def close(self) -> None:
        """Gracefully closes underlying database connections."""
        self.db_manager.close()
