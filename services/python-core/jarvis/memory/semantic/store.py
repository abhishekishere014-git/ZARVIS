"""Semantic vector store supporting sqlite-vec with graceful fallback."""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from jarvis.memory.errors import VectorStoreError
from jarvis.memory.semantic.embeddings import cosine_similarity
from jarvis.memory.semantic.sqlite_vec import is_sqlite_vec_available, load_sqlite_vec_extension
from jarvis.memory.structured.database import DatabaseManager

logger = logging.getLogger("jarvis.memory.semantic.store")


class SemanticMemoryStore:
    """Vector database indexing and KNN retrieval engine with graceful degradation."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        dimension: int = 128,
        table_name: str = "vec_memories",
    ) -> None:
        self.db_manager = db_manager
        self.dimension = dimension
        self.table_name = table_name
        self._is_degraded = not is_sqlite_vec_available()
        self._initialized = False

    def is_degraded(self) -> bool:
        """Indicates if store is running in pure-Python fallback mode without native sqlite-vec."""
        return self._is_degraded

    def initialize(self) -> None:
        """Initializes vector storage tables in the database."""
        if self._initialized:
            return

        conn = self.db_manager.connect()
        try:
            if not self._is_degraded:
                loaded = load_sqlite_vec_extension(conn)
                if loaded:
                    with conn:
                        conn.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS {self.table_name} (
                                memory_id TEXT PRIMARY KEY,
                                embedding BLOB,
                                metadata_json TEXT DEFAULT '{{}}'
                            );
                            """
                        )
                    self._initialized = True
                    return
                else:
                    self._is_degraded = True

            # Fallback mode: standard table storing JSON-serialized vectors
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fallback_vectors (
                        memory_id TEXT PRIMARY KEY,
                        vector_json TEXT NOT NULL,
                        metadata_json TEXT DEFAULT '{}'
                    );
                    """
                )
            self._initialized = True
            logger.info("SemanticMemoryStore initialized in graceful fallback mode.")
        except sqlite3.Error as exc:
            raise VectorStoreError(f"Failed to initialize semantic vector store: {exc}") from exc

    def index_record(
        self,
        record_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Indexes or updates a record's embedding vector."""
        self.initialize()
        conn = self.db_manager.connect()
        meta_json = json.dumps(metadata or {})

        try:
            if not self._is_degraded:
                load_sqlite_vec_extension(conn)
                # sqlite-vec serialize float array
                import sqlite_vec
                serialized = sqlite_vec.serialize_float32(vector)
                with conn:
                    conn.execute(
                        f"""
                        INSERT OR REPLACE INTO {self.table_name} (memory_id, embedding, metadata_json)
                        VALUES (?, ?, ?);
                        """,
                        (record_id, serialized, meta_json),
                    )
            else:
                with conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO fallback_vectors (memory_id, vector_json, metadata_json)
                        VALUES (?, ?, ?);
                        """,
                        (record_id, json.dumps(vector), meta_json),
                    )
        except Exception as exc:
            raise VectorStoreError(f"Failed to index vector for memory '{record_id}': {exc}") from exc

    def search_knn(
        self,
        query_vector: List[float],
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """Finds top-K most similar memories. Returns list of (memory_id, similarity_score)."""
        self.initialize()
        conn = self.db_manager.connect()

        try:
            if not self._is_degraded:
                load_sqlite_vec_extension(conn)
                import sqlite_vec
                query_blob = sqlite_vec.serialize_float32(query_vector)
                cursor = conn.cursor()
                # Query using vec_distance_cosine
                sql = f"""
                SELECT memory_id, vec_distance_cosine(embedding, ?) AS distance
                FROM {self.table_name}
                ORDER BY distance ASC
                LIMIT ?;
                """
                cursor.execute(sql, (query_blob, top_k * 2))
                rows = cursor.fetchall()

                results: List[Tuple[str, float]] = []
                for row in rows:
                    dist = float(row[1]) if row[1] is not None else 1.0
                    # Cosine distance to similarity: 1.0 - (dist / 2.0)
                    similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                    if similarity >= min_similarity:
                        results.append((row[0], similarity))
                    if len(results) >= top_k:
                        break
                return results
            else:
                # Fallback: compute cosine similarity in Python over stored vectors
                cursor = conn.cursor()
                cursor.execute("SELECT memory_id, vector_json FROM fallback_vectors;")
                rows = cursor.fetchall()

                scored: List[Tuple[str, float]] = []
                for row in rows:
                    mem_id = row[0]
                    vec = json.loads(row[1])
                    sim = cosine_similarity(query_vector, vec)
                    if sim >= min_similarity:
                        scored.append((mem_id, sim))

                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[:top_k]
        except Exception as exc:
            logger.warning("Vector search encountered error (%s); falling back to empty results.", exc)
            return []

    def delete_record(self, record_id: str) -> bool:
        """Removes a vector index entry for a memory ID."""
        self.initialize()
        conn = self.db_manager.connect()
        try:
            with conn:
                if not self._is_degraded:
                    load_sqlite_vec_extension(conn)
                    cursor = conn.execute(
                        f"DELETE FROM {self.table_name} WHERE memory_id = ?;", (record_id,)
                    )
                else:
                    cursor = conn.execute(
                        "DELETE FROM fallback_vectors WHERE memory_id = ?;", (record_id,)
                    )
                return cursor.rowcount > 0
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete vector for memory '{record_id}': {exc}") from exc
