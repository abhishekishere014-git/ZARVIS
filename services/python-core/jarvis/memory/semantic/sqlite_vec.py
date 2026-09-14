"""Extension loader and availability probing for sqlite-vec."""

import logging
import sqlite3
from typing import Optional

logger = logging.getLogger("jarvis.memory.sqlite_vec")

_SQLITE_VEC_CHECKED = False
_SQLITE_VEC_AVAILABLE = False


def is_sqlite_vec_available() -> bool:
    """Checks whether the sqlite-vec extension can be imported and initialized."""
    global _SQLITE_VEC_CHECKED, _SQLITE_VEC_AVAILABLE
    if _SQLITE_VEC_CHECKED:
        return _SQLITE_VEC_AVAILABLE

    try:
        import sqlite_vec
        test_db = sqlite3.connect(":memory:")
        test_db.enable_load_extension(True)
        sqlite_vec.load(test_db)
        test_db.enable_load_extension(False)
        test_db.close()
        _SQLITE_VEC_AVAILABLE = True
        logger.info("sqlite-vec extension is installed and fully operational.")
    except Exception as exc:
        _SQLITE_VEC_AVAILABLE = False
        logger.warning(
            "sqlite-vec is not available on this platform (%s). "
            "Semantic memory will operate in graceful fallback mode.",
            exc,
        )
    finally:
        _SQLITE_VEC_CHECKED = True

    return _SQLITE_VEC_AVAILABLE


def load_sqlite_vec_extension(conn: sqlite3.Connection) -> bool:
    """Loads the sqlite-vec extension into an active SQLite connection.

    Returns True if successfully loaded, False otherwise.
    """
    if not is_sqlite_vec_available():
        return False

    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception as exc:
        logger.error("Failed to load sqlite-vec extension into connection: %s", exc)
        return False
