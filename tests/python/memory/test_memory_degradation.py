"""Tests for graceful degradation when semantic stores or embeddings encounter errors."""

from pathlib import Path
import pytest
from jarvis.memory.config import MemoryConfig, SemanticMemoryConfig
from jarvis.memory.manager import MemoryManager
from jarvis.memory.models import RetrievalQuery


@pytest.mark.asyncio
async def test_graceful_degradation_when_semantic_disabled(tmp_path: Path) -> None:
    config = MemoryConfig(semantic=SemanticMemoryConfig(enabled=False))
    manager = MemoryManager(config=config, db_path=tmp_path / "degraded_test.db")

    await manager.store(content="Critical fact about system architecture", source="test")

    # Retrieval should work cleanly via structured store without crashing
    result = await manager.retrieve(RetrievalQuery(query="system architecture"))
    assert len(result.results) >= 1
    assert result.degraded is True
    assert "Critical fact" in result.results[0].record.content

    manager.close()
