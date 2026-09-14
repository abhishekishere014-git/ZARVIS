"""Bounded RecoveryEngine for mitigating task failures, retrying, and replanning."""

import logging
from typing import Tuple
from jarvis.agents.models import (
    AgentRecoveryAttempt,
    AgentRun,
    AgentTask,
    RecoveryState,
)

logger = logging.getLogger("jarvis.agents.recovery")


class RecoveryEngine:
    """Evaluates task failures and determines bounded mitigation strategies."""

    def __init__(
        self,
        max_step_retries: int = 2,
        max_replans: int = 2,
        max_recovery_attempts: int = 5,
    ) -> None:
        self.max_step_retries = max_step_retries
        self.max_replans = max_replans
        self.max_recovery_attempts = max_recovery_attempts

    def can_retry_step(self, task: AgentTask) -> bool:
        """Determines if a task can be retried immediately."""
        return task.retry_count < self.max_step_retries

    def can_replan(self, run: AgentRun) -> bool:
        """Determines if the run has budget remaining for a replan."""
        replan_count = sum(
            1 for rec in run.recovery_attempts if rec.state == RecoveryState.REPLANNING
        )
        return replan_count < self.max_replans

    def evaluate_failure(
        self,
        task: AgentTask,
        error: str,
        run: AgentRun,
    ) -> Tuple[RecoveryState, str]:
        """Evaluates a failure and selects the next recovery action.

        Returns:
            Tuple of (RecoveryState, action_description)
        """
        total_attempts = len(run.recovery_attempts)
        if total_attempts >= self.max_recovery_attempts:
            logger.warning("Global recovery attempt limit reached (%d). Aborting.", total_attempts)
            return RecoveryState.ABORTED, "Global recovery budget exhausted"

        # 1. Immediate retry if within step retry budget
        if self.can_retry_step(task):
            task.retry_count += 1
            action = f"Retry task '{task.id}' (Attempt {task.retry_count}/{self.max_step_retries})"
            attempt = AgentRecoveryAttempt(
                task_id=task.id,
                failure_reason=error,
                recovery_action=action,
                state=RecoveryState.RETRYING,
                attempt_number=task.retry_count,
            )
            run.recovery_attempts.append(attempt)
            return RecoveryState.RETRYING, action

        # 2. Replan if within replan budget
        if self.can_replan(run):
            action = f"Trigger replanning due to persistent failure in task '{task.id}'"
            attempt = AgentRecoveryAttempt(
                task_id=task.id,
                failure_reason=error,
                recovery_action=action,
                state=RecoveryState.REPLANNING,
                attempt_number=total_attempts + 1,
            )
            run.recovery_attempts.append(attempt)
            return RecoveryState.REPLANNING, action

        # 3. Terminal failure
        action = f"No further recovery possible for task '{task.id}'. Terminal failure."
        attempt = AgentRecoveryAttempt(
            task_id=task.id,
            failure_reason=error,
            recovery_action=action,
            state=RecoveryState.ABORTED,
            attempt_number=total_attempts + 1,
        )
        run.recovery_attempts.append(attempt)
        return RecoveryState.ABORTED, action
