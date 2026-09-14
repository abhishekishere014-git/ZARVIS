"""Tests for Phase 05 Autonomous Agents interacting with MemoryManager."""

from pathlib import Path
import pytest
from jarvis.agents.factory import build_agent_system
from jarvis.agents.models import AgentState
from jarvis.memory.manager import MemoryManager
from jarvis.tools.factory import build_tool_system


@pytest.mark.asyncio
async def test_agent_orchestration_with_memory(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    memory_db = tmp_path / "agent_memory.db"

    memory_mgr = MemoryManager(db_path=memory_db)
    tool_system = build_tool_system(workspace_dir=workspace_dir)
    agent_system = build_agent_system(
        tool_system=tool_system,
        checkpoint_dir=tmp_path / "checkpoints",
        memory=memory_mgr,
    )

    # 1. Pre-seed memory with an architectural fact
    await memory_mgr.store(
        content="The executive stakeholder requested emphasis on modular micro-kernel design",
        source="user",
    )

    # 2. Run autonomous goal
    goal = "Create a project presentation for executive stakeholders on AI Assistant Architecture"
    final_resp = await agent_system.orchestrator.run(goal)

    assert final_resp.status == AgentState.COMPLETED
    assert final_resp.task_statistics["completed"] >= 3

    # 3. Check that Research and Verifier agents stored facts in memory
    mem_count = memory_mgr.repository.count()
    assert mem_count >= 2

    # Check search over agent-produced memory
    retrieval = await memory_mgr.retrieve("presentation")
    assert len(retrieval.results) >= 1

    memory_mgr.close()
