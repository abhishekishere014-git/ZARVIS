"""Tests for preference deduplication, superseding updates, and confidence tracking."""

from pathlib import Path
from jarvis.memory.models import MemoryScope
from jarvis.memory.structured.database import DatabaseManager
from jarvis.memory.structured.repository import MemoryRepository


def test_preference_superseding(tmp_path: Path) -> None:
    db_mgr = DatabaseManager(db_path=tmp_path / "dedup_test.db")
    repo = MemoryRepository(db_mgr)

    # 1. Initial preference
    pref1 = repo.upsert_preference(
        preference_key="theme",
        preference_value="light",
        scope=MemoryScope.USER,
    )
    assert pref1.content == "Preference theme: light"
    assert repo.count() == 1

    # 2. User updates preference to dark
    pref2 = repo.upsert_preference(
        preference_key="theme",
        preference_value="dark",
        scope=MemoryScope.USER,
    )
    # Must update the existing preference row, not duplicate
    assert pref2.id == pref1.id
    assert pref2.content == "Preference theme: dark"
    assert repo.count() == 1

    fetched = repo.get(pref1.id)
    assert fetched is not None
    assert fetched.content == "Preference theme: dark"

    db_mgr.close()
