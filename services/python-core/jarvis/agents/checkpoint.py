"""Lightweight checkpoint storage allowing interrupted agent runs to resume."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from jarvis.agents.models import AgentCheckpoint, AgentRun

logger = logging.getLogger("jarvis.agents.checkpoint")


class CheckpointStore:
    """Provides file-backed and in-memory persistence for active AgentRuns."""

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self.checkpoint_dir = checkpoint_dir
        if self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._memory_store: Dict[str, AgentCheckpoint] = {}

    def save(self, run: AgentRun) -> AgentCheckpoint:
        """Saves a checkpoint of the active run state."""
        checkpoint = AgentCheckpoint(run=run)
        self._memory_store[run.run_id] = checkpoint

        if self.checkpoint_dir:
            file_path = self.checkpoint_dir / f"{run.run_id}.json"
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(checkpoint.model_dump_json(indent=2))
            except Exception as exc:
                logger.warning("Failed to persist checkpoint to disk for run '%s': %s", run.run_id, exc)

        logger.debug("Checkpoint saved for run '%s' (State: %s)", run.run_id, run.state.value)
        return checkpoint

    def load(self, run_id: str) -> Optional[AgentCheckpoint]:
        """Loads a checkpoint by run_id."""
        if run_id in self._memory_store:
            return self._memory_store[run_id]

        if self.checkpoint_dir:
            file_path = self.checkpoint_dir / f"{run_id}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    checkpoint = AgentCheckpoint.model_validate(data)
                    self._memory_store[run_id] = checkpoint
                    return checkpoint
                except Exception as exc:
                    logger.error("Failed to load checkpoint file for run '%s': %s", run_id, exc)

        return None

    def delete(self, run_id: str) -> bool:
        """Removes a checkpoint."""
        removed = self._memory_store.pop(run_id, None) is not None
        if self.checkpoint_dir:
            file_path = self.checkpoint_dir / f"{run_id}.json"
            if file_path.exists():
                file_path.unlink(missing_ok=True)
                removed = True
        return removed
