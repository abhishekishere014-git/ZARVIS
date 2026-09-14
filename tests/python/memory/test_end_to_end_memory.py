"""Full end-to-end multi-turn conversation and restart persistence tests."""

from pathlib import Path
import pytest
from jarvis.memory.manager import MemoryManager
from jarvis.memory.models import MemoryType


@pytest.mark.asyncio
async def test_restart_persistence_lifecycle(tmp_path: Path) -> None:
    db_file = tmp_path / "persistence_lifecycle.db"

    # Session 1: Create manager, store fact and preference, then close
    mgr1 = MemoryManager(db_path=db_file)
    await mgr1.store(
        content="The lead architect on JARVIS is Abhishek",
        source="user",
        memory_type=MemoryType.FACT,
    )
    mgr1.repository.upsert_preference("editor", "neovim")
    mgr1.close()

    # Session 2: Simulating JARVIS process restart with fresh manager instance
    mgr2 = MemoryManager(db_path=db_file)
    assert mgr2.repository.count() == 2

    # Query persistent memory
    retrieval = await mgr2.retrieve("Who is the lead architect?")
    assert len(retrieval.results) >= 1
    top_content = retrieval.results[0].record.content
    assert "Abhishek" in top_content

    # Query preference
    pref_retrieval = await mgr2.retrieve("editor preference")
    pref_contents = [r.record.content for r in pref_retrieval.results]
    assert any("neovim" in c for c in pref_contents)

    mgr2.close()
