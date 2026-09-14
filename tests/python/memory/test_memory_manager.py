"""Tests for MemoryManager end-to-end write pipeline, consolidation, and retrieval."""

from pathlib import Path
import pytest
from jarvis.memory.manager import MemoryManager
from jarvis.memory.models import MemoryScope, MemoryType, TrustLevel


@pytest.mark.asyncio
async def test_memory_manager_store_and_retrieve(tmp_path: Path) -> None:
    db_file = tmp_path / "mgr_test.db"
    manager = MemoryManager(db_path=db_file)

    # 1. Store a memory through the write pipeline with secret
    stored = await manager.store(
        content="User secret token is sk-1234567890abcdefghijklmnopqrstuv and preferred language is Python",
        source="user",
        memory_type=MemoryType.FACT,
    )
    assert stored.id.startswith("mem_")
    # Must have redacted the API key
    assert "sk-" not in stored.content
    assert "[REDACTED_OPENAI_KEY]" in stored.content
    assert stored.trust_level == TrustLevel.USER_VERIFIED

    # 2. Add working memory message
    manager.append_working_message(role="user", content="How do we build JARVIS?")
    assert len(manager.get_working_messages()) == 1

    # 3. Retrieve
    retrieval = await manager.retrieve("preferred language")
    assert len(retrieval.results) >= 1
    assert "Python" in retrieval.results[0].record.content
    assert len(retrieval.working_messages) == 1

    # 4. Context formatting
    prompt_ctx = manager.build_context_for_prompt(retrieval)
    assert "Python" in prompt_ctx

    manager.close()


@pytest.mark.asyncio
async def test_memory_manager_consolidation(tmp_path: Path) -> None:
    db_file = tmp_path / "consolidation_test.db"
    manager = MemoryManager(db_path=db_file)

    # Add 1 trivial message and 1 memoryworthy message
    manager.append_working_message(role="user", content="hello")
    manager.append_working_message(role="user", content="The project root directory is located at C:/ZARVIS")

    promoted = await manager.consolidate()
    # Only the substantive message should be promoted
    assert promoted == 1

    assert manager.repository.count() == 1
    retrieval = await manager.retrieve("project root")
    assert len(retrieval.results) == 1

    manager.close()
