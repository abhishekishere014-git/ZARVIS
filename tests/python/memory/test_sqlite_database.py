"""Tests for SQLite connection manager, WAL mode, and filesystem safety."""

from pathlib import Path
import pytest
from jarvis.memory.errors import StorageError
from jarvis.memory.structured.database import DatabaseManager


def test_sqlite_in_memory_connection() -> None:
    db_mgr = DatabaseManager(db_path=Path(":memory:"))
    conn = db_mgr.connect()
    assert conn is not None
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    assert cursor.fetchone()[0] == 1
    db_mgr.close()


def test_sqlite_path_traversal_prevention(tmp_path: Path) -> None:
    allowed_root = tmp_path / "safe_data"
    allowed_root.mkdir()

    # Attempting to escape allowed root must raise StorageError
    unsafe_path = allowed_root / ".." / "escaped.db"
    with pytest.raises(StorageError) as exc_info:
        DatabaseManager(db_path=unsafe_path, base_allowed_dir=allowed_root)
    assert "escapes allowed root" in str(exc_info.value)


def test_sqlite_system_dir_prevention() -> None:
    with pytest.raises(StorageError) as exc_info:
        DatabaseManager(db_path=Path("C:/Windows/System32/evil.db"))
    assert "protected system directory" in str(exc_info.value)


def test_sqlite_wal_mode_on_disk(tmp_path: Path) -> None:
    db_file = tmp_path / "memory.db"
    db_mgr = DatabaseManager(db_path=db_file, wal_mode=True)
    conn = db_mgr.connect()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0].lower()
    assert mode == "wal"
    db_mgr.close()
