"""Repository implementing typed CRUD, indexed search, and deduplication for SQLite memory."""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from jarvis.memory.errors import StorageError
from jarvis.memory.models import (
    EmbeddingStatus,
    MemoryRecord,
    MemoryScope,
    MemoryType,
    RetrievalQuery,
    TrustLevel,
)
from jarvis.memory.structured.database import DatabaseManager

logger = logging.getLogger("jarvis.memory.repository")


class MemoryRepository:
    """Thread-safe persistence layer for structured memory records."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def _get_conn(self) -> sqlite3.Connection:
        return self.db_manager.connect()

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        """Hydrates a Pydantic MemoryRecord from a database row."""
        try:
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        return MemoryRecord(
            id=row["id"],
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            summary=row["summary"],
            scope=MemoryScope(row["scope"]),
            source=row["source"],
            importance=float(row["importance"]),
            confidence=float(row["confidence"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
            conversation_id=row["conversation_id"],
            task_id=row["task_id"],
            artifact_id=row["artifact_id"],
            project_id=row["project_id"],
            metadata=metadata,
            embedding_status=EmbeddingStatus(row["embedding_status"]),
            trust_level=TrustLevel(row["trust_level"]),
        )

    def insert(self, record: MemoryRecord) -> MemoryRecord:
        """Persists a new memory record into the database."""
        conn = self._get_conn()
        sql = """
        INSERT INTO memories (
            id, memory_type, content, summary, scope, source, importance, confidence,
            created_at, updated_at, expires_at, conversation_id, task_id, artifact_id,
            project_id, metadata_json, embedding_status, trust_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        try:
            with conn:
                conn.execute(
                    sql,
                    (
                        record.id,
                        record.memory_type.value,
                        record.content,
                        record.summary,
                        record.scope.value,
                        record.source,
                        record.importance,
                        record.confidence,
                        record.created_at,
                        record.updated_at,
                        record.expires_at,
                        record.conversation_id,
                        record.task_id,
                        record.artifact_id,
                        record.project_id,
                        json.dumps(record.metadata),
                        record.embedding_status.value,
                        record.trust_level.value,
                    ),
                )
            return record
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to insert memory record '{record.id}': {exc}") from exc

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        """Retrieves a memory record by its primary key ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE id = ?;", (memory_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def update(self, record: MemoryRecord) -> MemoryRecord:
        """Updates an existing memory record."""
        conn = self._get_conn()
        record.updated_at = datetime.now(timezone.utc).isoformat()
        sql = """
        UPDATE memories SET
            content = ?, summary = ?, importance = ?, confidence = ?, updated_at = ?,
            expires_at = ?, metadata_json = ?, embedding_status = ?, trust_level = ?
        WHERE id = ?;
        """
        try:
            with conn:
                cursor = conn.execute(
                    sql,
                    (
                        record.content,
                        record.summary,
                        record.importance,
                        record.confidence,
                        record.updated_at,
                        record.expires_at,
                        json.dumps(record.metadata),
                        record.embedding_status.value,
                        record.trust_level.value,
                        record.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise StorageError(f"Memory record with ID '{record.id}' not found for update.")
            return record
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to update memory record '{record.id}': {exc}") from exc

    def delete(self, memory_id: str) -> bool:
        """Deletes a memory record by ID. Returns True if deleted."""
        conn = self._get_conn()
        try:
            with conn:
                cursor = conn.execute("DELETE FROM memories WHERE id = ?;", (memory_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to delete memory record '{memory_id}': {exc}") from exc

    def search(self, query: RetrievalQuery) -> List[MemoryRecord]:
        """Executes structured search with criteria filtering, boundary scoping, and token limits."""
        conn = self._get_conn()
        conditions: List[str] = []
        params: List[Any] = []

        now_iso = datetime.now(timezone.utc).isoformat()
        if not query.include_expired:
            conditions.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(now_iso)

        if query.scope:
            conditions.append("scope = ?")
            params.append(query.scope.value)

        if query.project_id:
            conditions.append("(project_id = ? OR scope = 'global')")
            params.append(query.project_id)

        if query.conversation_id:
            conditions.append("(conversation_id = ? OR scope IN ('user', 'global', 'project'))")
            params.append(query.conversation_id)

        if query.memory_types:
            placeholders = ", ".join("?" for _ in query.memory_types)
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend(t.value for t in query.memory_types)

        if query.min_importance > 0.0:
            conditions.append("importance >= ?")
            params.append(query.min_importance)

        if query.min_confidence > 0.0:
            conditions.append("confidence >= ?")
            params.append(query.min_confidence)

        # Content keyword filtering
        if query.query and query.query.strip():
            keywords = [w.strip() for w in query.query.split() if len(w.strip()) > 2]
            if keywords:
                # Match at least one significant keyword
                sub_conds = ["(content LIKE ? OR summary LIKE ?)" for _ in keywords]
                conditions.append(f"({' OR '.join(sub_conds)})")
                for kw in keywords:
                    pattern = f"%{kw}%"
                    params.extend([pattern, pattern])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
        SELECT * FROM memories
        {where_clause}
        ORDER BY importance DESC, created_at DESC
        LIMIT ?;
        """
        params.append(query.top_k)

        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [self._row_to_record(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            raise StorageError(f"Search failed for query '{query.query}': {exc}") from exc

    def upsert_preference(
        self,
        preference_key: str,
        preference_value: str,
        scope: MemoryScope = MemoryScope.USER,
        source: str = "user",
    ) -> MemoryRecord:
        """Creates or updates a user preference, superseding prior values for the same key."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, memory_id FROM preferences WHERE preference_key = ? AND scope = ?;",
                (preference_key, scope.value),
            )
            existing = cursor.fetchone()

            if existing:
                pref_id, memory_id = existing[0], existing[1]
                # Update existing memory record
                with conn:
                    conn.execute(
                        """
                        UPDATE preferences
                        SET preference_value = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (preference_value, now, pref_id),
                    )
                    conn.execute(
                        """
                        UPDATE memories
                        SET content = ?, updated_at = ?, confidence = 1.0
                        WHERE id = ?;
                        """,
                        (f"Preference {preference_key}: {preference_value}", now, memory_id),
                    )
                record = self.get(memory_id)
                if not record:
                    raise StorageError(f"Failed to fetch updated preference memory '{memory_id}'.")
                return record
            else:
                # Create brand new preference and memory record
                record = MemoryRecord(
                    memory_type=MemoryType.PREFERENCE,
                    content=f"Preference {preference_key}: {preference_value}",
                    scope=scope,
                    source=source,
                    importance=0.9,
                    confidence=1.0,
                    metadata={"preference_key": preference_key, "preference_value": preference_value},
                )
                self.insert(record)

                pref_id = f"pref_{record.id[4:]}"
                with conn:
                    conn.execute(
                        """
                        INSERT INTO preferences (
                            id, preference_key, preference_value, scope, source, memory_id, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (pref_id, preference_key, preference_value, scope.value, source, record.id, now, now),
                    )
                return record
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to upsert preference '{preference_key}': {exc}") from exc

    def prune_expired(self) -> int:
        """Removes all expired records whose deadline has elapsed. Returns deletion count."""
        conn = self._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?;",
                    (now_iso,),
                )
                return cursor.rowcount
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to prune expired memories: {exc}") from exc

    def count(self, scope: Optional[MemoryScope] = None) -> int:
        """Returns total records in the memories table."""
        conn = self._get_conn()
        cursor = conn.cursor()
        if scope:
            cursor.execute("SELECT COUNT(*) FROM memories WHERE scope = ?;", (scope.value,))
        else:
            cursor.execute("SELECT COUNT(*) FROM memories;")
        return cursor.fetchone()[0]
