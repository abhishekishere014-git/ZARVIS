"""Tests for CheckpointStore saving, loading, and deleting run snapshots."""

from pathlib import Path
from jarvis.agents.checkpoint import CheckpointStore
from jarvis.agents.models import AgentGoal, AgentRun, AgentState


def test_checkpoint_store_in_memory_and_file(tmp_path: Path) -> None:
    store = CheckpointStore(checkpoint_dir=tmp_path)

    run = AgentRun(
        goal=AgentGoal(user_prompt="Persist state test"),
        state=AgentState.RUNNING,
    )

    chk = store.save(run)
    assert chk.run.run_id == run.run_id

    # Verify file written to disk
    file_path = tmp_path / f"{run.run_id}.json"
    assert file_path.exists()

    # Load checkpoint
    loaded = store.load(run.run_id)
    assert loaded is not None
    assert loaded.run.run_id == run.run_id
    assert loaded.run.state == AgentState.RUNNING

    # Delete
    assert store.delete(run.run_id) is True
    assert store.load(run.run_id) is None
    assert not file_path.exists()
