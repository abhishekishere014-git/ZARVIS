"""Observation normalization pipeline converting tool and task results into structured evidence."""

import time
from typing import Any, Dict, List, Optional
from jarvis.agents.models import AgentObservation
from jarvis.tools.models import ToolResult


class ObservationNormalizer:
    """Normalizes raw execution artifacts and tool results into structured AgentObservations."""

    @staticmethod
    def from_tool_result(
        task_id: str,
        result: ToolResult,
        evidence_keys: Optional[Dict[str, Any]] = None,
    ) -> AgentObservation:
        """Constructs an AgentObservation from a Phase 04 ToolResult."""
        evidence: Dict[str, Any] = {
            "execution_id": result.execution_id,
            "status": result.status.value,
            "artifacts": result.artifacts,
            **(evidence_keys or {}),
        }
        if result.output and isinstance(result.output, dict):
            # Extract common evidence metrics
            for metric_key in ("size_bytes", "paragraphs_count", "sheets_count", "slides_count"):
                if metric_key in result.output:
                    evidence[metric_key] = result.output[metric_key]

        return AgentObservation(
            task_id=task_id,
            tool_id=result.tool_id,
            status=result.status.value,
            output=result.output,
            artifacts=result.artifacts,
            duration_ms=result.duration_ms,
            evidence=evidence,
            error=result.error,
        )

    @staticmethod
    def from_agent_computation(
        task_id: str,
        output: Any,
        status: str = "success",
        artifacts: Optional[List[str]] = None,
        duration_ms: float = 0.0,
        evidence: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> AgentObservation:
        """Constructs an AgentObservation from an agent's internal analysis or reasoning."""
        return AgentObservation(
            task_id=task_id,
            tool_id=None,
            status=status,
            output=output,
            artifacts=artifacts or [],
            duration_ms=duration_ms,
            evidence=evidence or {},
            error=error,
        )
