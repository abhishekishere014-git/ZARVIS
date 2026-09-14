# JARVIS Tri-Tier Memory Engine Architecture

## 1. System Overview

The **Tri-Tier Memory Engine** provides multi-timescale persistent memory for JARVIS, bridging transient immediate dialogue, durable relational facts, and vector semantic retrieval.

```
                    JARVIS AGENT RUNTIME / AI ROUTER
                                   │
                                   ▼
                             MemoryManager
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  TIER 1: WORKING │     │ TIER 2:DATABASE  │     │ TIER 3: SEMANTIC │
│   MEMORY (RAM)   │     │ (SQLite Store)   │     │   (sqlite-vec)   │
│                  │     │                  │     │                  │
│ - Sliding Window │     │ - Fact Store     │     │ - Vector Knn     │
│ - Token Budget   │     │ - Preferences    │     │ - Cosine Fallback│
│ - Priority Queue │     │ - Tasks History  │     │ - Hash Embeddings│
│ - Overflow Sum   │     │ - Migrations     │     │ - Top-K Matches  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                            MemoryRetriever
                        (Deterministic 6-Factor)
                                   │
                                   ▼
                         MemoryContextBuilder
                        (Passive Context Guard)
```

---

## 2. Tier Details

### Tier 1: Working Memory (`jarvis.memory.working`)
* **Storage:** In-memory sliding window (`WorkingMemory`).
* **Characteristics:** Microsecond latency (<1ms), bounded capacity by message count (`max_messages`) and token estimates (`max_estimated_tokens`).
* **Priority Eviction:** Preserves high-priority directives while evicting lowest-priority items into a running overflow summary (`_summary`).
* **Context Isolation:** Maintains dedicated slots for `system_context` and `active_task_context` that are never discarded during conversation cycling.

### Tier 2: Structured Storage (`jarvis.memory.structured`)
* **Storage:** SQLite file at `data/memory/jarvis-memory.db` operated in WAL mode with a 5000ms busy timeout.
* **Migrations:** Transactional, versioned schema upgrades managed by `MigrationManager`.
* **Entities:**
  * `memories`: Primary provenance-tracked entity table.
  * `conversations` & `messages`: Multi-turn conversational history.
  * `facts`: Subject-predicate-object semantic triples.
  * `preferences`: Upsertable, deduplicated user preferences.
  * `tasks`: Execution logs and objective summaries.
  * `artifacts`: Metadata for files generated in the Phase 04 sandbox.
  * `memory_events`: Audit trail for memory write/read operations.

### Tier 3: Semantic Retrieval (`jarvis.memory.semantic`)
* **Storage:** Vector embeddings indexed via `sqlite-vec` (v0.1.9) with graceful degradation to an internal JSON-vector cosine similarity search when native extensions are absent.
* **Embeddings:** Extensible `EmbeddingProvider` protocol with a default `HashEmbeddingProvider` producing deterministic 128-dimensional unit vectors with zero external API dependencies.

---

## 3. Scope Isolation Model

To prevent cross-domain contamination or accidental context bleeding between projects, memory records are partitioned by `MemoryScope`:
1. `SESSION`: Ephemeral context expiring after 24 hours.
2. `CONVERSATION`: Direct conversation history.
3. `PROJECT`: Isolated project domain knowledge (strictly barred from surfacing in unrelated project queries).
4. `USER`: Durable personal facts and preferences.
5. `GLOBAL`: Universal application knowledge.
