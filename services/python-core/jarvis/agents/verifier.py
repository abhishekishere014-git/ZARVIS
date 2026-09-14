"""Evidence-based verifier inspecting artifacts, tool executions, and logical task outputs."""

from pathlib import Path
from typing import Dict, List, Optional
from jarvis.agents.models import (
    AgentPlan,
    AgentStepResult,
    AgentTask,
    AgentVerification,
    TaskState,
    VerificationState,
)
from jarvis.tools.sandbox import FileSystemSandbox


class AgentVerifier:
    """Performs rigorous, multi-faceted verification on agent outputs and generated artifacts."""

    def __init__(self, sandbox: Optional[FileSystemSandbox] = None) -> None:
        self.sandbox = sandbox

    def verify_step(
        self,
        task: AgentTask,
        result: AgentStepResult,
    ) -> AgentVerification:
        """Independently verifies that a task's reported results are supported by concrete evidence."""
        # 1. Execution status check
        if result.status != TaskState.COMPLETED:
            return AgentVerification(
                task_id=task.id,
                state=VerificationState.FAILED,
                score=0.0,
                notes=f"Task execution did not complete successfully: {result.error or 'unknown error'}",
            )

        verified_artifacts: List[str] = []
        missing_evidence: List[str] = []

        # 2. Tool verification: verify all tool observations reported success
        for obs in result.observations:
            if obs.tool_id and obs.status != "success":
                return AgentVerification(
                    task_id=task.id,
                    state=VerificationState.FAILED,
                    score=0.0,
                    missing_evidence=[f"tool:{obs.tool_id}"],
                    notes=f"Tool '{obs.tool_id}' reported failure: {obs.error}",
                )

        # 3. Artifact verification: verify physical existence and non-zero size
        target_artifacts = list(set(result.artifacts + [str(a) for a in task.artifacts]))
        for art_path_str in target_artifacts:
            path_obj = Path(art_path_str)
            if self.sandbox:
                try:
                    resolved = self.sandbox.resolve_safe_path(path_obj)
                except Exception:
                    resolved = path_obj
            else:
                resolved = path_obj

            if not resolved.exists():
                missing_evidence.append(f"missing_file:{resolved.name}")
            elif resolved.stat().st_size == 0:
                missing_evidence.append(f"empty_file:{resolved.name}")
            else:
                verified_artifacts.append(str(resolved))

        # 4. Logical payload check: task must return substantial output or verified artifacts
        has_output = result.output is not None and str(result.output).strip() != ""
        if not has_output and not verified_artifacts:
            missing_evidence.append("empty_result_payload")

        # 5. Determine State
        if missing_evidence:
            if verified_artifacts or has_output:
                state = VerificationState.PARTIAL
                score = 0.5
                notes = f"Partial verification: missing evidence for {missing_evidence}"
            else:
                state = VerificationState.FAILED
                score = 0.0
                notes = f"Verification failed: missing critical evidence {missing_evidence}"
        else:
            state = VerificationState.PASSED
            score = 1.0
            notes = "All tool executions, outputs, and artifacts successfully verified."

        return AgentVerification(
            task_id=task.id,
            state=state,
            score=score,
            verified_artifacts=verified_artifacts,
            missing_evidence=missing_evidence,
            notes=notes,
        )

    def verify_plan(
        self,
        plan: AgentPlan,
        verifications: Dict[str, AgentVerification],
    ) -> bool:
        """Verifies that every task in the execution plan has achieved PASSED verification status."""
        for task in plan.tasks:
            ver = verifications.get(task.id)
            if not ver or ver.state != VerificationState.PASSED:
                return False
        return True
