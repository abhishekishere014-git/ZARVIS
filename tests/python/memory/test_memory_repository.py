"""Tests for typed MemoryRepository CRUD, migrations, and indexed search."""

from pathlib import Path
from jarvis.memory.models import (
    MemoryRecord,
    MemoryScope,
    MemoryType,
    RetrievalQuery,
)
from jarvis.memory.structured.database import DatabaseManager
from jarvis.memory.structured.repository import MemoryRepository


def test_repository_crud(tmp_path: Path) -> None:
    db_mgr = DatabaseManager(db_path=tmp_path / "repo_test.db")
    repo = MemoryRepository(db_mgr)

    # 1. Insert
    rec = MemoryRecord(
        content="Primary server runs on port 8765",
        memory_type=MemoryType.FACT,
        scope=MemoryScope.PROJECT,
        project_id="proj_jarvis",
    )
    saved = repo.insert(rec)
    assert saved.id == rec.id
    assert repo.count() == 1

    # 2. Get
    fetched = repo.get(saved.id)
    assert fetched is not None
    assert fetched.content == rec.content
    assert fetched.project_id == "proj_jarvis"

    # 3. Update
    fetched.content = "Primary server runs on port 9000"
    repo.update(fetched)
    updated = repo.get(saved.id)
    assert updated is not None
    assert updated.content == "Primary server runs on port 9000"

    # 4. Search
    query = RetrievalQuery(query="server port", project_id="proj_jarvis")
    results = repo.search(query)
    assert len(results) == 1
    assert results[0].id == saved.id

    # 5. Delete
    deleted = repo.delete(saved.id)
    assert deleted is True
    assert repo.count() == 0
    assert repo.get(saved.id) is None

    db_mgr.close()
