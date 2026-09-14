"""Tests for parallel execution of independent tasks within DAG waves."""

import asyncio
import time
from pathlib import Path
import pytest
from jarvis.agents.base import AgentContext, BaseAgent
from jarvis.agents.factory import build_agent_system
from jarvis.agents.models import (
    AgentDefinition,
    AgentPlan,
    AgentRun,
    AgentState,
    AgentStepResult,
    AgentTask,
    TaskState,
)


class AsyncSleepAgent(BaseAgent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(AgentDefinition(id=agent_id, name="Sleep Agent", description="Sleeps"))

    async def execute(self, context: AgentContext) -> AgentStepResult:
        sleep_secs = context.task.input_data.get("sleep", 0.1)
        await asyncio.sleep(sleep_secs)
        return AgentStepResult(task_id=context.task.id, agent_id=self.id, status=TaskState.COMPLETED, output="slept")


@pytest.mark.asyncio
async def test_independent_tasks_execute_in_parallel(tmp_path: Path) -> None:
    agent_system = build_agent_system(checkpoint_dir=tmp_path / "checkpoints")

    # Register two sleep agents
    a1 = AsyncSleepAgent("agent.sleep1")
    a2 = AsyncSleepAgent("agent.sleep2")
    agent_system.registry.register(a1)
    agent_system.registry.register(a2)

    # Wave with two independent tasks each sleeping 0.2s
    t1 = AgentTask(id="t1", title="Sleep 1", description="D1", assigned_agent="agent.sleep1", input_data={"sleep": 0.2})
    t2 = AgentTask(id="t2", title="Sleep 2", description="D2", assigned_agent="agent.sleep2", input_data={"sleep": 0.2})
    plan = AgentPlan(goal_id="g_parallel", tasks=[t1, t2])

    waves = agent_system.plan_validator.validate_and_sort(plan)
    assert len(waves) == 1
    assert len(waves[0]) == 2  # Both in same wave

    from jarvis.agents.models import AgentGoal
    run = AgentRun(goal=AgentGoal(user_prompt="Parallel test"))
    start = time.perf_counter()
    wave_coroutines = [
        agent_system.orchestrator._execute_single_task(run, task, [])
        for task in waves[0]
    ]
    results = await asyncio.gather(*wave_coroutines)
    elapsed = time.perf_counter() - start

    assert len(results) == 2
    # If run sequentially it would take >= 0.4s. Concurrently it takes ~0.2s (< 0.35s).
    assert elapsed < 0.35, f"Expected parallel execution under 0.35s, took {elapsed:.2f}s"
