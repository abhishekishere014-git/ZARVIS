"""Master AgentOrchestrator coordinating goal decomposition, DAG execution waves, and verification."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from jarvis.agents.approval import ApprovalManager
from jarvis.agents.base import AgentContext
from jarvis.agents.checkpoint import CheckpointStore
from jarvis.agents.executor import AgentTaskExecutor
from jarvis.agents.models import (
    AgentFinalResponse,
    AgentGoal,
    AgentObservation,
    AgentPlan,
    AgentRun,
    AgentState,
    AgentStepResult,
    AgentTask,
    RecoveryState,
    TaskState,
    VerificationState,
)
from jarvis.agents.plan_validator import PlanValidator
from jarvis.agents.recovery import RecoveryEngine
from jarvis.agents.registry import AgentRegistry
from jarvis.agents.synthesizer import FinalSynthesizer
from jarvis.agents.verifier import AgentVerifier
from jarvis.core.bus import AsyncEventBus
from jarvis.protocol.models import JarvisEvent

logger = logging.getLogger("jarvis.agents.orchestrator")


class AgentOrchestrator:
    """Deterministic, bounded multi-agent state machine orchestrating tasks, tools, and verification."""

    def __init__(
        self,
        registry: AgentRegistry,
        plan_validator: PlanValidator,
        executor: AgentTaskExecutor,
        verifier: AgentVerifier,
        recovery_engine: RecoveryEngine,
        approval_manager: ApprovalManager,
        checkpoint_store: CheckpointStore,
        synthesizer: FinalSynthesizer,
        event_bus: Optional[AsyncEventBus] = None,
        memory: Optional[Any] = None,
        max_runtime_seconds: float = 300.0,
        max_total_steps: int = 20,
    ) -> None:
        self.registry = registry
        self.plan_validator = plan_validator
        self.executor = executor
        self.verifier = verifier
        self.recovery_engine = recovery_engine
        self.approval_manager = approval_manager
        self.checkpoint_store = checkpoint_store
        self.synthesizer = synthesizer
        self.event_bus = event_bus
        self.memory = memory
        self.max_runtime_seconds = max_runtime_seconds
        self.max_total_steps = max_total_steps
        self._active_runs: Dict[str, AgentRun] = {}
        self._cancelled_runs: set = set()
        self._paused_runs: set = set()

    async def _emit_event(
        self,
        event_type: str,
        run_id: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emits correlated agent lifecycle telemetry onto AsyncEventBus."""
        if not self.event_bus or not self.event_bus.is_running:
            return

        data = {
            "run_id": run_id,
            "task_id": task_id,
            "agent_id": agent_id,
            **(payload or {}),
        }
        event = JarvisEvent(
            id=f"evt_{run_id}_{int(time.time() * 1000)}",
            type=event_type,
            correlation_id=run_id,
            payload=data,
        )
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to publish event '%s': %s", event_type, exc)

    async def run(self, goal: str | AgentGoal) -> AgentFinalResponse:
        """Executes an autonomous multi-agent workflow from a goal to a verified final answer."""
        if isinstance(goal, str):
            agent_goal = AgentGoal(user_prompt=goal)
        else:
            agent_goal = goal

        run = AgentRun(goal=agent_goal)
        self._active_runs[run.run_id] = run
        start_time = time.perf_counter()

        await self._emit_event("agent.started", run.run_id, payload={"goal": agent_goal.user_prompt})

        try:
            # 1. Planning Phase
            run.state = AgentState.PLANNING
            await self._emit_event("agent.planning", run.run_id)

            planner = self.registry.get("agent.planner")
            planner_task = AgentTask(
                id="planning_task",
                title="Goal Decomposition",
                description=agent_goal.user_prompt,
                assigned_agent=planner.id,
                input_data={"goal_prompt": agent_goal.user_prompt},
            )
            planner_context = AgentContext(
                run_id=run.run_id,
                task=planner_task,
                agent_definition=planner.definition,
                router=self.executor.router,
            )

            planner_result = await planner.execute(planner_context)
            if planner_result.status != TaskState.COMPLETED or not planner_result.output:
                raise RuntimeError(f"Planner failed to generate plan: {planner_result.error}")

            raw_plan = planner_result.output.get("plan")
            plan = AgentPlan.model_validate(raw_plan)
            run.plan = plan

            # 2. Plan Validation & Topological Sort
            execution_waves = self.plan_validator.validate_and_sort(plan)
            run.state = AgentState.READY
            await self._emit_event(
                "agent.plan.created",
                run.run_id,
                payload={"tasks_count": len(plan.tasks), "waves_count": len(execution_waves)},
            )
            self.checkpoint_store.save(run)

            # 3. Execution Waves
            run.state = AgentState.RUNNING
            collected_observations: List[AgentObservation] = []

            for wave_idx, wave in enumerate(execution_waves):
                # Check cancellation or pause
                if run.run_id in self._cancelled_runs:
                    run.state = AgentState.CANCELLED
                    await self._emit_event("agent.cancelled", run.run_id)
                    break

                # Execute independent tasks concurrently within the wave
                wave_coroutines = [
                    self._execute_single_task(run, task, collected_observations)
                    for task in wave
                ]
                wave_results = await asyncio.gather(*wave_coroutines)

                # Check if any task failed terminally
                for task, (step_res, verification) in zip(wave, wave_results):
                    run.task_results[task.id] = step_res
                    run.verifications[task.id] = verification
                    collected_observations.extend(step_res.observations)
                    run.artifacts.extend(step_res.artifacts)

                    if verification.state == VerificationState.PASSED:
                        run.completed_tasks.append(task.id)
                    else:
                        run.failed_tasks.append(task.id)
                        run.state = AgentState.FAILED
                        run.error = f"Task '{task.id}' failed verification: {verification.notes}"

                self.checkpoint_store.save(run)
                if run.state == AgentState.FAILED:
                    break

            # 4. Final State Evaluation
            if run.state not in (AgentState.FAILED, AgentState.CANCELLED):
                all_passed = self.verifier.verify_plan(plan, run.verifications)
                run.state = AgentState.COMPLETED if all_passed else AgentState.FAILED
                if all_passed:
                    await self._emit_event("agent.completed", run.run_id)
                else:
                    await self._emit_event("agent.failed", run.run_id)

        except Exception as exc:
            run.state = AgentState.FAILED
            run.error = str(exc)
            logger.error("Agent run '%s' encountered fatal error: %s", run.run_id, exc, exc_info=True)
            await self._emit_event("agent.failed", run.run_id, payload={"error": str(exc)})

        run.duration_ms = (time.perf_counter() - start_time) * 1000.0
        run.end_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.checkpoint_store.save(run)

        # 5. Final Answer Synthesis
        final_response = await self.synthesizer.synthesize(run)
        return final_response

    async def _execute_single_task(
        self,
        run: AgentRun,
        task: AgentTask,
        prior_observations: List[AgentObservation],
    ) -> tuple[AgentStepResult, Any]:
        """Executes a single task with bounded retries and verification."""
        run.current_task_id = task.id
        await self._emit_event(
            "agent.step.started",
            run.run_id,
            task_id=task.id,
            agent_id=task.assigned_agent,
        )

        while True:
            step_result = await self.executor.execute_task(
                run_id=run.run_id,
                task=task,
                prior_observations=prior_observations,
            )

            await self._emit_event(
                "agent.verification.started",
                run.run_id,
                task_id=task.id,
            )
            verification = self.verifier.verify_step(task, step_result)
            await self._emit_event(
                "agent.verification.completed",
                run.run_id,
                task_id=task.id,
                payload={"status": verification.state.value, "score": verification.score},
            )

            if verification.state == VerificationState.PASSED:
                await self._emit_event(
                    "agent.step.completed",
                    run.run_id,
                    task_id=task.id,
                    agent_id=task.assigned_agent,
                )
                return step_result, verification

            # Handle recovery
            recovery_state, action = self.recovery_engine.evaluate_failure(
                task=task,
                error=verification.notes,
                run=run,
            )
            await self._emit_event(
                "agent.recovery.started",
                run.run_id,
                task_id=task.id,
                payload={"action": action, "recovery_state": recovery_state.value},
            )

            if recovery_state == RecoveryState.RETRYING:
                logger.info("Retrying task '%s': %s", task.id, action)
                continue
            else:
                # Abort task
                await self._emit_event(
                    "agent.step.failed",
                    run.run_id,
                    task_id=task.id,
                    agent_id=task.assigned_agent,
                    payload={"error": verification.notes},
                )
                return step_result, verification

    def cancel_run(self, run_id: str) -> bool:
        """Cancels an active or pending agent run."""
        self._cancelled_runs.add(run_id)
        if run_id in self._active_runs:
            run = self._active_runs[run_id]
            run.state = AgentState.CANCELLED
            self.checkpoint_store.save(run)
            logger.info("Cancelled active agent run '%s'", run_id)
            return True
        return True

    def pause_run(self, run_id: str) -> bool:
        """Pauses an active agent run."""
        if run_id in self._active_runs:
            self._paused_runs.add(run_id)
            run = self._active_runs[run_id]
            run.state = AgentState.PAUSED
            self.checkpoint_store.save(run)
            logger.info("Paused agent run '%s'", run_id)
            return True
        return False

    def resume_run(self, run_id: str) -> Optional[AgentRun]:
        """Resumes a paused or checkpointed agent run."""
        checkpoint = self.checkpoint_store.load(run_id)
        if checkpoint:
            self._paused_runs.discard(run_id)
            self._cancelled_runs.discard(run_id)
            run = checkpoint.run
            run.state = AgentState.RUNNING
            self._active_runs[run_id] = run
            logger.info("Resumed agent run '%s'", run_id)
            return run
        return None
