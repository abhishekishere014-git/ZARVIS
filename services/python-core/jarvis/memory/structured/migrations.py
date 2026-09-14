"""Idempotent, transactional SQLite migrations engine for JARVIS Memory Store."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import List, Tuple
from jarvis.memory.errors import MigrationError

logger = logging.getLogger("jarvis.memory.migrations")

# Ordered list of migrations: (version, migration_name, sql_script)
MIGRATIONS: List[Tuple[int, str, str]] = [
    (
        1,
        "001_initial_memory_schema",
        """
        -- Core durable memories table
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            scope TEXT NOT NULL,
            source TEXT NOT NULL,
            importance REAL NOT NULL DEFAULT 0.5,
            confidence REAL NOT NULL DEFAULT 0.8,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT,
            conversation_id TEXT,
            task_id TEXT,
            artifact_id TEXT,
            project_id TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            embedding_status TEXT NOT NULL DEFAULT 'pending',
            trust_level TEXT NOT NULL DEFAULT 'model_generated'
        );

        -- Conversations table
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        -- Messages table
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        -- Dedicated Facts table
        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL UNIQUE,
            subject TEXT,
            predicate TEXT,
            object TEXT,
            confidence REAL NOT NULL DEFAULT 0.8,
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
        );

        -- Dedicated Preferences table
        CREATE TABLE IF NOT EXISTS preferences (
            id TEXT PRIMARY KEY,
            preference_key TEXT NOT NULL,
            preference_value TEXT NOT NULL,
            scope TEXT NOT NULL,
            source TEXT NOT NULL,
            memory_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
        );

        -- Tasks history table
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            goal_prompt TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        -- Artifacts registry table
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            task_id TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        -- Summaries table
        CREATE TABLE IF NOT EXISTS summaries (
            id TEXT PRIMARY KEY,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Memory lifecycle audit events table
        CREATE TABLE IF NOT EXISTS memory_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            memory_id TEXT,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        "002_add_indexes",
        """
        CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);
        CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
        CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
        CREATE INDEX IF NOT EXISTS idx_memories_conversation ON memories(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_memories_task ON memories(task_id);
        CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id);
        CREATE INDEX IF NOT EXISTS idx_memories_expires ON memories(expires_at);

        CREATE INDEX IF NOT EXISTS idx_preferences_key ON preferences(preference_key);
        CREATE INDEX IF NOT EXISTS idx_preferences_scope ON preferences(scope);
        CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
        """,
    ),
]


class MigrationManager:
    """Coordinates versioned SQLite schema migrations."""

    @classmethod
    def apply_migrations(cls, conn: sqlite3.Connection) -> int:
        """Applies all pending migrations within an isolated transaction.

        Returns total newly applied migrations.
        """
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TEXT NOT NULL
                    );
                    """
                )

            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations;")
            applied_versions = {row[0] for row in cursor.fetchall()}

            applied_count = 0
            for version, name, sql in MIGRATIONS:
                if version not in applied_versions:
                    logger.info("Applying memory migration %03d: %s...", version, name)
                    try:
                        with conn:
                            conn.executescript(sql)
                            conn.execute(
                                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                                (version, name, datetime.now(timezone.utc).isoformat()),
                            )
                        applied_count += 1
                        logger.info("Successfully applied migration %03d.", version)
                    except Exception as exc:
                        logger.critical("Migration %03d failed: %s", version, exc)
                        raise MigrationError(f"Failed to apply migration {version} ({name}): {exc}") from exc

            return applied_count
        except sqlite3.Error as err:
            raise MigrationError(f"SQLite migration initialization error: {err}") from err
