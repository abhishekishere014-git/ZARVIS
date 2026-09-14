"""SQLite connection supervisor and filesystem safety enforcer for Structured Memory."""

import logging
import os
from pathlib import Path
import sqlite3
from typing import Optional
from jarvis.memory.errors import StorageError
from jarvis.memory.structured.migrations import MigrationManager

logger = logging.getLogger("jarvis.memory.database")


class DatabaseManager:
    """Oversees SQLite database lifecycle, path validation, WAL pragmas, and migrations."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        base_allowed_dir: Optional[Path] = None,
        wal_mode: bool = True,
        busy_timeout_ms: int = 5000,
    ) -> None:
        self.is_memory = (db_path is not None and str(db_path) == ":memory:")
        self.wal_mode = wal_mode
        self.busy_timeout_ms = busy_timeout_ms
        self._conn: Optional[sqlite3.Connection] = None

        if self.is_memory:
            self.db_path = Path(":memory:")
        else:
            default_path = (base_allowed_dir or Path("./data")) / "memory" / "jarvis-memory.db"
            target_path = (db_path or default_path).resolve()
            
            # Security boundary validation: prevent path traversal or system file tampering
            if base_allowed_dir is not None:
                allowed_root = base_allowed_dir.resolve()
                try:
                    target_path.relative_to(allowed_root)
                except ValueError:
                    raise StorageError(
                        f"Database path '{target_path}' escapes allowed root '{allowed_root}'."
                    )
            
            # Explicitly guard against critical system roots
            path_str = str(target_path).replace("\\", "/").lower()
            if "/windows/system32" in path_str or "/etc" in path_str:
                raise StorageError(f"Access to protected system directory '{target_path}' is denied.")

            target_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = target_path

    def connect(self) -> sqlite3.Connection:
        """Establishes or returns the active database connection with safety pragmas."""
        if self._conn is not None:
            return self._conn

        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=self.busy_timeout_ms / 1000.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row

            # Apply robust pragmas
            if not self.is_memory and self.wal_mode:
                conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms};")
            conn.execute("PRAGMA foreign_keys = ON;")

            # Apply versioned migrations automatically
            MigrationManager.apply_migrations(conn)

            self._conn = conn
            logger.debug("DatabaseManager connected to '%s'", self.db_path)
            return conn
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to connect to SQLite database at '{self.db_path}': {exc}") from exc

    def close(self) -> None:
        """Closes the underlying database connection gracefully."""
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            finally:
                self._conn = None
                logger.debug("DatabaseManager closed connection.")
